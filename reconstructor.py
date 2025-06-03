"""
UBIFS Filesystem reconstructor

This module reconstructs a filesystem from UBIFS nodes.
It builds directory structures, file metadata, and extracts file contents.
Now supports symbolic links and hard links.

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
FileInfo = namedtuple('FileInfo', ['inum', 'name', 'type', 'size', 'mode', 'uid', 'gid', 'atime', 'mtime', 'ctime', 'nlink'])
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
        
        # Link tracking
        self.hard_links: Dict[int, List[str]] = defaultdict(list)  # inum -> [paths]
        self.symlink_targets: Dict[int, str] = {}       # inum -> target_path
        self.created_files: Dict[int, str] = {}         # inum -> first_created_path

    def add_inode_node(self, node_data:Struct):
        """Add an inode node to the filesystem"""
        inum = node_data.inum
        size, mode, uid, gid, atime, mtime, ctime, nlink = 0,0,0,0,0,0,0,1
        if (inum!=0):
            size = node_data.size
            mode = node_data.mode
            uid = node_data.uid
            gid = node_data.gid
            atime = node_data.atime_sec
            mtime = node_data.mtime_sec
            ctime = node_data.ctime_sec
            # Get link count if available
            nlink = getattr(node_data, 'nlink', 1)
        
        # Determine file type from mode
        file_type = mode & 0xF000
        
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
            ctime=ctime,
            nlink=nlink
        )
        
        self.inodes[inum] = file_info
        print(f"\tAdded inode {inum}: type={hex(file_type)}, size={size}, nlink={nlink}")

    def add_dent_node(self, node_data:Struct, parent_inum: int = None):
        """Add a directory entry node"""
        inum = node_data.inum
        name = node_data["name"].decode('utf-8') if isinstance(node_data["name"], bytes) else node_data["name"]
        entry_type = node_data.type
        
        # Try to get parent from the node data itself
        if parent_inum is None:
            # Check various possible field names for parent directory
            parent_inum = (getattr(node_data, 'parent_inum', None) or 
                          getattr(node_data, 'dir_inum', None) or 
                          getattr(node_data, 'pinum', None) or
                          getattr(node_data, 'parent', None))
        
        # If still no parent, assume root directory
        if parent_inum is None:
            parent_inum = 1
        
        print(f"\tDENT: {name} (inum={inum}) in parent {parent_inum}")

        dir_entry = DirEntry(
            inum=inum,
            name=name,
            type=entry_type,
            parent_inum=parent_inum
        )
        
        self.dir_entries[parent_inum].append(dir_entry)
        print(f"\tAdded directory entry: {name} -> inode {inum} (parent: {parent_inum})")

    def add_data_node(self, node_data: Struct):
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
        """Build the directory tree structure"""
        print("\nBuilding directory tree...")
        
        # Initialize root directory
        if 1 not in self.directory_tree:
            self.directory_tree[1] = {}
            self.inode_paths[1] = "/"
        
        # Process directory entries
        for parent_inum, entries in self.dir_entries.items():
            if parent_inum not in self.directory_tree:
                self.directory_tree[parent_inum] = {}
            
            for entry in entries:
                # Skip . and .. entries
                if entry.name in ['.', '..']:
                    continue
                
                self.directory_tree[parent_inum][entry.name] = entry.inum
                
                # Build full path
                parent_path = self.inode_paths.get(parent_inum, "/")
                if parent_path == "/":
                    full_path = f"/{entry.name}"
                else:
                    full_path = f"{parent_path}/{entry.name}"
                
                self.inode_paths[entry.inum] = full_path
                
                # Track hard links (multiple paths to same inode)
                if entry.inum in self.inodes:
                    inode_info = self.inodes[entry.inum]
                    
                    # Add to hard links tracking
                    self.hard_links[entry.inum].append(full_path)
                    
                    # If this is a directory, initialize its tree entry
                    if inode_info.type == self.UBIFS_ITYPE_DIR:
                        if entry.inum not in self.directory_tree:
                            self.directory_tree[entry.inum] = {}
        
        # Extract symbolic link targets after all paths are built
        self._extract_symlink_targets()

    def _extract_symlink_targets(self):
        """Extract symbolic link targets after all data is processed"""
        print("Extracting symbolic link targets...")
        for inum, inode_info in self.inodes.items():
            if inode_info.type == self.UBIFS_ITYPE_LNK:
                target = self.reconstruct_symlink_target(inum)
                if target:
                    self.symlink_targets[inum] = target
                    print(f"  Symlink inode {inum} -> '{target}'")
                else:
                    print(f"  Symlink inode {inum} -> (no target found)")
                    # Debug: show what data blocks we have for this inode
                    if inum in self.data_blocks:
                        print(f"    Data blocks available: {len(self.data_blocks[inum])}")
                        for block in self.data_blocks[inum]:
                            print(f"      Block {block.block_num}: {len(block.data)} bytes - {block.data[:50]}")
                    else:
                        print(f"    No data blocks found for symlink inode {inum}")

    def reconstruct_symlink_target(self, inum: int) -> str:
        """Reconstruct symbolic link target from data blocks"""
        if inum not in self.data_blocks:
            return ""
        
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
        
        # Decode as UTF-8 string (symlink target)
        try:
            return content.decode('utf-8').rstrip('\0')
        except UnicodeDecodeError:
            return content.decode('utf-8', errors='replace').rstrip('\0')

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
                
                if inode_info.type == self.UBIFS_ITYPE_DIR:
                    dir_path = self.output_dir / path.lstrip('/')
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"Created directory: {dir_path}")
        
        # Create regular files and symbolic links
        for inum, inode_info in self.inodes.items():
            if inode_info.type == self.UBIFS_ITYPE_REG:
                self._create_regular_file(inum, inode_info)
            elif inode_info.type == self.UBIFS_ITYPE_LNK:
                self._create_symbolic_link(inum, inode_info)

    def _create_regular_file(self, inum: int, inode_info: FileInfo):
        """Create a regular file, handling hard links properly"""
        paths = self.hard_links.get(inum, [])
        
        if not paths:
            return
        
        # Sort paths to ensure consistent creation order
        paths.sort()
        
        # Create the first instance of the file
        first_path = paths[0]
        file_path = self.output_dir / first_path.lstrip('/')
        
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
        self.created_files[inum] = str(file_path)
        
        # Create hard links to the remaining paths
        if len(paths) > 1:
            for additional_path in paths[1:]:
                link_path = self.output_dir / additional_path.lstrip('/')
                
                # Ensure parent directory exists
                link_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Remove existing file if it exists
                    if link_path.exists():
                        link_path.unlink()
                    
                    # Create hard link
                    os.link(file_path, link_path)
                    print(f"Created hard link: {link_path} -> {file_path}")
                except (OSError, NotImplementedError) as e:
                    # Fallback: copy the file if hard links aren't supported
                    print(f"Hard link failed ({e}), copying instead: {link_path}")
                    with open(file_path, 'rb') as src, open(link_path, 'wb') as dst:
                        dst.write(src.read())
                    try:
                        os.chmod(link_path, inode_info.mode & 0o7777)
                        os.utime(link_path, (inode_info.atime, inode_info.mtime))
                    except (OSError, PermissionError):
                        pass

    def _create_symbolic_link(self, inum: int, inode_info: FileInfo):
        """Create symbolic links"""
        paths = self.hard_links.get(inum, [])
        target = self.symlink_targets.get(inum, "")
        
        if not paths or not target:
            return
        
        # Create symbolic link for each path
        for path in paths:
            link_path = self.output_dir / path.lstrip('/')
            
            # Ensure parent directory exists
            link_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Remove existing file if it exists
                if link_path.exists() or link_path.is_symlink():
                    link_path.unlink()
                
                # Create symbolic link
                os.symlink(target, link_path)
                print(f"Created symbolic link: {link_path} -> {target}")
            except (OSError, NotImplementedError) as e:
                print(f"Failed to create symbolic link {link_path} -> {target}: {e}")

    def print_filesystem_info(self):
        """Print filesystem information"""
        print("\n" + "="*60)
        print("FILESYSTEM RECONSTRUCTION SUMMARY")
        print("="*60)
        
        print(f"Total inodes: {len(self.inodes)}")
        print(f"Total directory entries: {sum(len(entries) for entries in self.dir_entries.values())}")
        print(f"Total data blocks: {sum(len(blocks) for blocks in self.data_blocks.values())}")
        
        # Debug: Show all directory entries by parent
        print(f"\nDirectory entries by parent:")
        for parent_inum, entries in self.dir_entries.items():
            parent_path = self.inode_paths.get(parent_inum, f"<inum {parent_inum}>")
            print(f"  Parent {parent_inum} ({parent_path}):")
            for entry in entries:
                print(f"    {entry.name} -> inode {entry.inum}")
        
        # Count file types
        reg_files = sum(1 for info in self.inodes.values() if info.type == self.UBIFS_ITYPE_REG)
        directories = sum(1 for info in self.inodes.values() if info.type == self.UBIFS_ITYPE_DIR)
        symlinks = sum(1 for info in self.inodes.values() if info.type == self.UBIFS_ITYPE_LNK)
        
        print(f"\nRegular files: {reg_files}")
        print(f"Directories: {directories}")
        print(f"Symbolic links: {symlinks}")
        
        # Count hard links
        hard_link_count = sum(1 for paths in self.hard_links.values() if len(paths) > 1)
        print(f"Files with hard links: {hard_link_count}")
        
        print("\nDirectory structure:")
        self._print_tree(1, "", True)
        
        if self.symlink_targets:
            print("\nSymbolic links:")
            for inum, target in self.symlink_targets.items():
                paths = self.hard_links.get(inum, [])
                for path in paths:
                    print(f"  {path} -> {target}")
        
        # Show hard links
        hard_linked_inodes = {inum: paths for inum, paths in self.hard_links.items() if len(paths) > 1}
        if hard_linked_inodes:
            print("\nHard links:")
            for inum, paths in hard_linked_inodes.items():
                print(f"  Inode {inum}:")
                for path in paths:
                    print(f"    {path}")
        
        print(f"\nFiles will be extracted to: {self.output_dir.absolute()}")

    def _print_tree(self, inum: int, prefix: str, is_last: bool):
        """Recursively print directory tree"""
        if inum not in self.inode_paths:
            return
        
        name = Path(self.inode_paths[inum]).name or "/"
        
        # Add type indicator
        type_indicator = ""
        if inum in self.inodes:
            inode_info = self.inodes[inum]
            if inode_info.type == self.UBIFS_ITYPE_LNK:
                target = self.symlink_targets.get(inum, "")
                type_indicator = f" -> {target}" if target else " -> (empty target)"
            elif len(self.hard_links.get(inum, [])) > 1:
                type_indicator = " (hardlinked)"
        
        print(f"{prefix}{'└── ' if is_last else '├── '}{name}{type_indicator}")
        
        if inum in self.directory_tree:
            children = list(self.directory_tree[inum].items())
            for i, (child_name, child_inum) in enumerate(children):
                is_last_child = (i == len(children) - 1)
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._print_tree(child_inum, new_prefix, is_last_child)
    
    def process_parsed_nodes(self, headers:List[Struct], parsed_nodes: List[Struct]):
        """Process a list of parsed UBIFS nodes"""
        print("Processing parsed nodes...")
        
        # First pass: collect all nodes by type
        ino_nodes = []
        dent_nodes = []
        data_nodes = []
        
        for i in range(len(parsed_nodes)):
            print(f"Node #{i}: {UBIFS_NODE_TYPES.get(headers[i].node_type, "UNKNOWN"):8} @ 0x{offsets[i]:06X}")
            node_type = headers[i].node_type
            
            if node_type == 0:  # INO_NODE
                ino_nodes.append(parsed_nodes[i])
            elif node_type == 2:  # DENT_NODE
                dent_nodes.append(parsed_nodes[i])
            elif node_type == 1:  # DATA_NODE
                data_nodes.append(parsed_nodes[i])
        
        # Process in correct order
        print(f"\nProcessing {len(ino_nodes)} inode nodes...")
        for node in ino_nodes:
            self.add_inode_node(node)
            
        print(f"\nProcessing {len(data_nodes)} data nodes...")
        for node in data_nodes:
            self.add_data_node(node)
            
        print(f"\nProcessing {len(dent_nodes)} directory entry nodes...")
        for node in dent_nodes:
            # Try to determine parent from the node structure
            parent_inum = getattr(node, 'parent_inum', None) or getattr(node, 'dir_inum', None)
            self.add_dent_node(node, parent_inum)
        
        # Build filesystem structure
        self.build_directory_tree()
        self.print_filesystem_info()
        self.create_filesystem_structure()


if __name__ == "__main__":
    (offsets, headers, nodes) = parse_ubifs_image(input("\nPath (relative or absolute) to the UBIFS '.img' file:\n"))
    #(offsets, headers, nodes) = parse_ubifs_image("UBIFS-Explorer\\files.img")
    reconstructor = UBIFSFilesystemReconstructor()
    reconstructor.process_parsed_nodes(headers, nodes)