"""
UBIFS Filesystem reconstructor

This module reconstructs a filesystem from UBIFS nodes.
It builds directory structures, file metadata, and extracts file contents.

The filesystem reconstruction will follow this logical flow:
    INO NODES   → Create file/dir metadata
        ↓
    DENT NODES  → Build directory structure and filename mappings
        ↓
    DATA NODES  → Reconstruct file contents
        ↓
    Final Assembly → Create the actual filesystem on disk
"""
from construct import Struct
from explorer import parse_ubifs_image, UBIFS_NODE_TYPES
from collections import defaultdict, namedtuple
from pathlib import Path
import os
from typing import Dict, List, Optional, Tuple, Any

# Data structures for filesystem reconstruction
FileInfo = namedtuple('FileInfo', ['inum', 'name', 'type', 'size', 'mode', 'uid', 'gid', 'atime', 'mtime', 'ctime'])
DirEntry = namedtuple('DirEntry', ['inum', 'name', 'type', 'parent_inum'])
DataBlock = namedtuple('DataBlock', ['inum', 'block_num', 'data'])

class UBIFSFilesystemReconstructor:
    def __init__ (self, output_dir:str = "reconstructed_fs"):
        self.output_dir = Path(output_dir)

        # Constants
        self.UBIFS_ITYPE_REG = 0x8000   # Regular file
        self.UBIFS_ITYPE_DIR = 0x4000   # Directory
        self.UBIFS_ITYPE_LNK = 0xA000   # Symbolic link

        # Node storage by type
        #   {inum : FileInfo}
        self.inodes: Dict[int, FileInfo] = {}           
        #   {parent_inum : [DirEntry]}
        self.dir_entries: Dict[int, List[DirEntry]] = defaultdict(list)  
        #   {inum : [DataBlock]}
        self.data_blocks: Dict[int, List[DataBlock]] = defaultdict(list) 
        
        # Filesystem structure
        self.directory_tree: Dict[int, Dict] = {}       # inum -> {name: child_inum}
        self.inode_paths: Dict[int, str] = {}           # inum -> full_path

    def add_inode_node(self, node_data: Struct):
        """Add an inode node to the filesystem"""
        inum = node_data.inum
        size, mode, uid, gid, atime, mtime, ctime = 0,0,0,0,0,0,0
        
        if (inum != 0):
            size = node_data.size
            mode = node_data.mode
            uid = node_data.uid
            gid = node_data.gid
            atime = node_data.atime_sec
            mtime = node_data.mtime_sec
            ctime = node_data.ctime_sec
        
        # Determine file type from mode
        file_type = mode & 0xF000
        
        # For symbolic links, check if target is embedded in inode
        symlink_target = ""
        if file_type == self.UBIFS_ITYPE_LNK:
            # check if there's a 'data' field in the inode
            if hasattr(node_data, 'data') and node_data.data:
                try:
                    symlink_target = node_data.data.decode('utf-8').rstrip('\x00')
                    print(f"\tFound symlink target in inode: '{symlink_target}'")
                except:
                    pass
            
        
        file_info = FileInfo(
            inum=inum,
            name="",  # Will be filled from DENT nodes
            type=file_type,
            size=size,
            mode=mode,
            uid=uid,
            gid=gid,
            atime=atime,
            mtime=mtime,
            ctime=ctime
        )
        
        self.inodes[inum] = file_info
        
        # Store symlink target separately if found
        if symlink_target:
            if not hasattr(self, 'symlink_targets'):
                self.symlink_targets = {}
            self.symlink_targets[inum] = symlink_target
        
        print(f"\tAdded inode {inum}: type={hex(file_type)}, size={size}")

    def add_dent_node(self, node_data:Struct, parent_inum: int = None):
        """Add a directory entry node"""
        inum = node_data.inum
        name = node_data["name"].decode('utf-8') if isinstance(node_data["name"], bytes) else node_data["name"]
        entry_type = node_data.type
        
        # If parent_inum not provided, try to determine from context
        if parent_inum is None:
            parent_inum = 1  # Assume root directory
        
        # TODO: if parent_inum is not a inode, you can recover the file

        dir_entry = DirEntry(
            inum=inum,
            name=name,
            type=entry_type,
            parent_inum=parent_inum
        )
        
        self.dir_entries[parent_inum].append(dir_entry)
        print(f"\tAdded directory entry: {name} -> inode {inum} (parent: {parent_inum})")

    def add_data_node(self, node_data: Dict[str, Any]):
        """Add a data node"""
        inum = node_data.inum
        block_num = node_data.block
        data = node_data.data
        
        data_block = DataBlock(
            inum=inum,
            block_num=block_num,
            data=data
        )

        # TODO: if inum is not a inode, you can recover the file
        
        self.data_blocks[inum].append(data_block)
        print(f"\tAdded data block for inode {inum}: block {block_num}, size {len(data)}")

    def build_directory_tree(self):
        """Build the directory tree structure using recursive approach"""
        print("\nBuilding directory tree...")
        
        # Initialize root directory
        if 1 not in self.directory_tree:
            self.directory_tree[1] = {}
            self.inode_paths[1] = "/"
        
        # Recursively build paths starting from root
        self._build_paths_recursive(1, "/")
        print("Directory tree built successfully")

    def _build_paths_recursive(self, parent_inum: int, parent_path: str):
        """Recursively build directory paths"""
        if parent_inum not in self.dir_entries:
            return
        
        # Initialize parent in directory tree if needed
        if parent_inum not in self.directory_tree:
            self.directory_tree[parent_inum] = {}
        
        for entry in self.dir_entries[parent_inum]:
            # Skip . and .. entries
            if entry.name in ['.', '..']:
                continue
            
            # Add to directory tree
            self.directory_tree[parent_inum][entry.name] = entry.inum
            
            # Build full path
            if parent_path == "/":
                full_path = f"/{entry.name}"
            else:
                full_path = f"{parent_path}/{entry.name}"
            
            self.inode_paths[entry.inum] = full_path
            print(f"  Added: {full_path} (inum: {entry.inum})")
            
            # If this is a directory, initialize and recurse
            if entry.inum in self.inodes:
                inode_info = self.inodes[entry.inum]
                if (inode_info.mode & 0xF000) == self.UBIFS_ITYPE_DIR:
                    if entry.inum not in self.directory_tree:
                        self.directory_tree[entry.inum] = {}
                    # Recurse into subdirectory
                    self._build_paths_recursive(entry.inum, full_path)


    def reconstruct_file_content(self, inum: int) -> bytes:
        """Reconstruct file content from data blocks"""
        if inum not in self.data_blocks:
            return b''
        
        # Sort data blocks by block number
        blocks = sorted(self.data_blocks[inum], key=lambda x: x.block_num)
        
        # Concatenate data
        content = b''
        for block in blocks:
            content += block.data
        
        # Trim to actual file size if known
        if inum in self.inodes:
            file_size = self.inodes[inum].size
            if file_size > 0 and len(content) > file_size:
                content = content[:file_size]
        
        return content

    def create_filesystem_structure(self):
        """Create the actual filesystem structure on disk"""
        print(f"\nCreating filesystem structure in {self.output_dir}...")
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Create directories first
        for inum, path in self.inode_paths.items():
            if inum in self.inodes:
                inode_info = self.inodes[inum]
                
                if ((inode_info.mode & 0xF000) == self.UBIFS_ITYPE_DIR):
                    dir_path = self.output_dir / path.lstrip('/')
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"Created directory: {dir_path}")

        # Create files
        for inum, path in self.inode_paths.items():
            if inum in self.inodes:
                inode_info = self.inodes[inum]
                
                if ((inode_info.mode & 0xF000) == self.UBIFS_ITYPE_REG):
                    file_path = self.output_dir / path.lstrip('/')
                    
                    # Ensure parent directory exists
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Reconstruct and write file content
                    content = self.reconstruct_file_content(inum)
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    # Set file permissions and timestamps
                    try:
                        os.chmod(file_path, inode_info.mode & 0o7777)
                        os.utime(file_path, (inode_info.atime, inode_info.mtime))
                    except (OSError, PermissionError):
                        pass  # Skip if we can't set permissions/times
                    
                    print(f"Created file: {file_path} ({len(content)} bytes)")
                
                elif ((inode_info.mode & 0xF000) == self.UBIFS_ITYPE_LNK):
                    # Symbolic link
                    link_path = self.output_dir / path.lstrip('/')
                    
                    # Ensure parent directory exists
                    link_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Get the link target
                    target = self.symlink_targets[inum]
                    
                    if target:
                        try:
                            # Remove existing file/link if it exists
                            if link_path.exists() or link_path.is_symlink():
                                link_path.unlink()
                            
                            # Create the symbolic link
                            os.symlink(target, link_path)
                            
                            print(f"Created symlink: {link_path} -> {target}")
                            
                        except OSError as e:
                            print(f"Failed to create symlink {link_path} -> {target}: {e}")
                    else:
                        print(f"Warning: Empty target for symlink {link_path}")

    def print_filesystem_info(self):
        """Print filesystem information"""
        print("\n" + "="*60)
        print("FILESYSTEM RECONSTRUCTION SUMMARY")
        print("="*60)
        
        # Count different file types
        regular_files = sum(1 for info in self.inodes.values() 
                        if (info.mode & 0xF000) == self.UBIFS_ITYPE_REG)
        directories = sum(1 for info in self.inodes.values() 
                        if (info.mode & 0xF000) == self.UBIFS_ITYPE_DIR)
        symlinks = sum(1 for info in self.inodes.values() 
                    if (info.mode & 0xF000) == self.UBIFS_ITYPE_LNK)
        
        print(f"Total inodes: {len(self.inodes)}")
        print(f"  - Regular files: {regular_files}")
        print(f"  - Directories: {directories}")
        print(f"  - Symbolic links: {symlinks}")
        print(f"Total directory entries: {sum(len(entries) for entries in self.dir_entries.values())}")
        print(f"Total data blocks: {sum(len(blocks) for blocks in self.data_blocks.values())}")
        
        print("\nDirectory structure:")
        self._print_tree(1, "", True)
        
        print(f"\nFiles will be extracted to: {self.output_dir.absolute()}")

    def _print_tree(self, inum: int, prefix: str, is_last: bool):
        """Recursively print directory tree"""
        if inum not in self.inode_paths:
            return
        
        name = Path(self.inode_paths[inum]).name or "/"
        
        # Add link target information for symbolic links
        extra_info = ""
        if inum in self.inodes:
            inode_info = self.inodes[inum]
            if (inode_info.mode & 0xF000) == self.UBIFS_ITYPE_LNK:
                target = self.symlink_targets[inum]
                extra_info = f" -> {target}" if target else " -> <empty>"
        
        print(f"{prefix}{'└── ' if is_last else '├── '}{name}{extra_info}")
        
        if inum in self.directory_tree:
            children = list(self.directory_tree[inum].items())
            for i, (child_name, child_inum) in enumerate(children):
                is_last_child = (i == len(children) - 1)
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._print_tree(child_inum, new_prefix, is_last_child)
    
    def process_parsed_nodes(self, headers:List[Struct], parsed_nodes: List[Struct]):
        """Process a list of parsed UBIFS nodes"""
        print("Processing parsed nodes...")
        
        for i in range(len(parsed_nodes)):
            print(f"Node #{i}: {UBIFS_NODE_TYPES.get(headers[i].node_type, "UNKNOWN"):8} @ 0x{offsets[i]:06X}")
            node_type = headers[i].node_type
            
            if node_type == 0:  # INO_NODE
                self.add_inode_node(parsed_nodes[i])
            elif node_type == 2:  # DENT_NODE
                # You may need to determine parent_inum from context
                self.add_dent_node(parsed_nodes[i], parsed_nodes[i]["key_inum"])
            elif node_type == 1:  # DATA_NODE
                self.add_data_node(parsed_nodes[i])
        
        # Build filesystem structure
        self.build_directory_tree()
        self.print_filesystem_info()
        self.create_filesystem_structure()


if __name__ == "__main__":
    image = input("\nPath (relative or absolute) to the UBIFS '.img' file:\n")
    (offsets, headers, nodes) = parse_ubifs_image(image)
    #(offsets, headers, nodes) = parse_ubifs_image("UBIFS-Explorer\\files.img")
    reconstructor = UBIFSFilesystemReconstructor(output_dir=(Path(image).stem))
    reconstructor.process_parsed_nodes(headers, nodes)