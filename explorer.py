"""
UBIFS image explorer

This script analyzes the internal structure of a UBIFS image and displays it to the user.
"""

from construct import Struct, Int32ul, Int8ul, Int64ul, Int16ul, Bytes, Array, Padding, GreedyBytes
from pathlib import Path

# UBIFS constants
UBIFS_NODE_MAGIC = 0x06101831
UBIFS_HEADER_SIZE = 24
UBIFS_KEY_LEN = 16
UBIFS_MAX_HMAC_LEN = 64
UBIFS_MAX_HASH_LEN = 64

#############################
#   [STRUCT DECLARATION]    #
#############################

# UBIFS common node header
UBIFSHeader:Struct = Struct(
    "magic" / Int32ul,      # UBIFS node magic number (%UBIFS_NODE_MAGIC)
    "crc32" / Int32ul,      # CRC-32 checksum of the node header
    "sqnum" / Int64ul,      # sequence number
    "len" / Int32ul,        # full node length
    "node_type" / Int8ul,   # node type
    "group_type" / Int8ul,  # node group type
    "padding" / Padding(2)
)

# 0: INO_NODE
UBIFSInoNode:Struct = Struct(
    "inum" / Int32ul,           # Inode number
    "block" / Int32ul,
    "crc" / Bytes(UBIFS_KEY_LEN-8),

    "creat_sqnum" / Int64ul,    # Sequence number at time of creation
    "size" / Int64ul,           # Inode size in bytes (amount of uncompressed data)

    "atime_sec" / Int64ul,      # access time seconds
    "ctime_sec" / Int64ul,      # creation time seconds
    "mtime_sec" / Int64ul,      # modification time seconds
    
    "atime_nsec" / Int32ul,     # access time (ns)
    "ctime_nsec" / Int32ul,     # creation time (ns)
    "mtime_nsec" / Int32ul,     # modification time (ns)

    "nlink" / Int32ul,          # number of hard links  
    "uid" / Int32ul,            # User ID
    "gid" / Int32ul,            # Group ID
    "mode" / Int32ul,           # access flags  
    "flags" / Int32ul,          # per-inode flags (%UBIFS_COMPR_FL, %UBIFS_SYNC_FL, etc)
    
    "data_len" /Int32ul,        # inode data length
    "xattr_cnt" / Int32ul,      # count of extended attributes this inode has
    "xattr_size" / Int32ul,     # summarized size of all extended attributes in bytes

    "padding1" / Padding(4),
    "xattr_names" / Int32ul,    # sum of lengths of all extended attribute names belonging to this inode
    "compr_type" / Int16ul,     # compression type used for this inode
    "padding2" / Padding(26),

    "data" / GreedyBytes        # Remaining is inline data (if any)
)

UBIFSInoRouteNode:Struct = Struct(
    "inum" / Int32ul,           # Inode number
    "block" / Int32ul,
    "crc" / Bytes(UBIFS_KEY_LEN-8),
    "creat_sqnum" / Int64ul,    # Sequence number at time of creation
    "size" / Int64ul,           # Inode size in bytes (amount of uncompressed data)

    "data" / GreedyBytes
)

# 1: DATA_NODE
UBIFSDataNode:Struct = Struct(
    "inum" / Int32ul,           # Inode number
    "block" / Int32ul,
    "crc" / Bytes(UBIFS_KEY_LEN-8),
    "size" / Int32ul,           # uncompressed data size in bytes
    "compr_type" / Int16ul,     # compression type (%UBIFS_COMPR_NONE, %UBIFS_COMPR_LZO, etc)
    "compr_size" / Int16ul,     # compressed data size in bytes, only valid when data is encrypted
    "data" / GreedyBytes
)

# 2: DENT_NODE
UBIFSDentNode:Struct = Struct(
    "key_inum" / Int32ul,           # Inode number
    "block" / Int32ul,
    "crc" / Bytes(UBIFS_KEY_LEN-8),
    "inum" / Int64ul,       # Target Inode Number
    "padding1" / Padding(1),
    "type" / Int8ul,        # type of the target inode (%UBIFS_ITYPE_REG, %UBIFS_ITYPE_DIR, etc)
    "nlen" / Int16ul,       # name length
    "cookie" / Int32ul,     # A 32bits random number, used to construct a 64bits identifier.
    "name" / Bytes(lambda this: this.nlen)
)

# 3: XENT_NODE TODO: Review it
UBIFSXentNode:Struct = Struct(
    "inum" / Int64ul,
    "type" / Int8ul,
    "nlen" / Int8ul,
    "padding" / Padding(2),
    "name_hash" / Int32ul,
    "name" / Bytes(lambda this: this.nlen)
)

# 4: TRUN_NODE
UBIFSTrunNode:Struct = Struct(
    "inum" / Int32ul,
    "padding" / Padding(12),
    "old_size" / Int64ul,   # size before truncation
    "new_size" / Int64ul    # size after truncation
)

# 5: PAD_NODE
UBIFSPadNode:Struct = Struct(
    "pad_len" / Int32ul,
    "padding" / GreedyBytes
)

# 6: SB_NODE
UBIFSSuperblockNode:Struct = Struct(
    "padding" / Padding(2),
	"key_hash" / Int8ul,    # type of hash function used in keys
	"key_fmt" / Int8ul,     # format of the key
	"flags" / Int32ul,      # file-system flags (%UBIFS_FLG_BIGLPT, etc)
	"min_io_size" / Int32ul,
	"leb_size" / Int32ul,   # logical eraseblock size in bytes
	"leb_cnt" / Int32ul,    # count of LEBs used by file-system
	"max_leb_cnt" / Int32ul,
	"max_bud_bytes" / Int64ul,
	"log_lebs" / Int32ul,
	"lpt_lebs" / Int32ul,
	"orph_lebs" / Int32ul,
	"jhead_cnt" / Int32ul,
	"fanout" / Int32ul,
	"lsave_cnt" / Int32ul,
	"fmt_version" / Int32ul,
	"default_compr" / Int16ul,
	"padding1" / Padding(2),
	"rp_uid" / Int32ul,
	"rp_gid" / Int32ul,
	"rp_size" / Int64ul,
	"time_gran" / Int32ul,
	"uuid" / Bytes(16),
	"ro_compat_version" / Int32ul,
	"hmac" / Bytes(UBIFS_MAX_HMAC_LEN),
	"hmac_wkm" / Bytes(UBIFS_MAX_HMAC_LEN),
	"hash_algo" / Int16ul,
	"hash_mst" / Bytes(UBIFS_MAX_HASH_LEN),
	"padding2" / Padding(3774)
)

# 7: MST_NODE
UBIFSMasterNode:Struct = Struct(
    "highest_inum" / Int64ul,
    "cmt_no" / Int64ul,
    "flags" / Int32ul,
    "log_lnum" / Int32ul,
    "root_lnum" / Int32ul,
    "root_offs" / Int32ul,
    "root_len" / Int32ul,
    "gc_lnum" / Int32ul,
    "ihead_lnum" / Int32ul,
    "ihead_offs" / Int32ul,
    "index_size" / Int64ul,
    "total_free" / Int64ul,
    "total_dirty" / Int64ul,
    "total_used" / Int64ul,
    "total_dead" / Int64ul,
    "total_dark" / Int64ul,
    "lpt_lnum" / Int32ul,
    "lpt_offs" / Int32ul,
    "nhead_lnum" / Int32ul,
    "nhead_offs" / Int32ul,
    "ltab_lnum" / Int32ul,
    "ltab_offs" / Int32ul,
    "lsave_lnum" / Int32ul,
    "lsave_offs" / Int32ul,
    "lscan_lnum" / Int32ul,
    "empty_lebs" / Int32ul,
    "idx_lebs" / Int32ul,
    "leb_cnt" / Int32ul,
    "hash_root_idx" / Bytes(UBIFS_MAX_HASH_LEN),
    "hash_lpt" / Bytes(UBIFS_MAX_HASH_LEN),
    "hmac" / Bytes(UBIFS_MAX_HMAC_LEN),
    "padding" / Padding(152)
)

# 8: REF_NODE
UBIFSRefNode:Struct = Struct(
    "lnum" / Int32ul,
    "offs" / Int32ul,
    "jhead" / Int8ul,
    "padding" / Padding(7)
)

# Branch used in IDX_NODE
UBIFSBranch:Struct = Struct(
    "lnum" / Int32ul,
    "offs" / Int32ul,
    "len" / Int32ul,
    "key" / Bytes(lambda this: this.len)
)

# 9: IDX_NODE
UBIFSIdxNode:Struct = Struct(
    "child_cnt" / Int16ul,
    "level" / Int16ul,
    "branches" / GreedyBytes # TODO: Differenciate between the branches
)

# 10: CS_NODE
UBIFSCsNode:Struct = Struct(
    "cmt_no" / Int64ul
)

# 11: ORPH_NODE
UBIFSOrphNode:Struct = Struct(
    "cmt_no" / Int64ul,     # commit number (also top bit is set on the last node of the commit)
    "inos" / GreedyBytes    # inode numbers of orphans
)

# UNKNOWN
UBIFSUnknownNode:Struct = Struct(
    "data" / GreedyBytes
)

# Mapping of node types (partial list from UBIFS source)
UBIFS_NODE_TYPES:dict = {
    0: "INO_NODE",  # [Inode node]: stores metadata for files and directories.
    1: "DATA_NODE", # [Data node]: contains actual file content.
    2: "DENT_NODE", # [Directory entry node]: links filenames to inode numbers.
    3: "XENT_NODE", # [Extended attribute node]: stores extended attributes for files.
    4: "TRUN_NODE", # [Truncation node]: used to truncate files.
    5: "PAD_NODE",  # [Padding node]: used to pad unused space in logical erase blocks (LEBs).
    6: "SB_NODE",   # [Superblock node]: contains filesystem-wide information.
    7: "MST_NODE",  # [Master node]: holds pointers to key filesystem structures.
    8: "REF_NODE",  # [Reference node]: used in the journal to reference other nodes.
    9: "IDX_NODE",  # [Index node]: part of the indexing structure for fast lookup.
    10: "CS_NODE",  # [Commit start node]: marks the beginning of a commit operation.
    11: "ORPH_NODE" # [Orphan node]: tracks inodes that have been deleted but not yet purged.
}



#############################
#   [FUNCTION DECLARATION]  #
#############################
def process_node(node_type:str, payload_size:int, f) -> Struct:
    """
    This function will parse the content of a particular node into a 'Struct'
    
    Arguments:
        node_type       - Either from 'UBIFS_NODE_TYPES' or 'UNKNOWN' 
        payload_size    - Length of the payload of the node
        f               - File from which the information is being parsed
    """
    node:Struct = None

    if node_type == "UNKNOWN" or payload_size == 0:
        node = UBIFSUnknownNode.parse(content)
    elif payload_size < 0:
        raise Exception(msg="Payload cannot be smaller than 0")
    else:
        content = f.read(payload_size)
        if (len(content) == payload_size):
            # There is as much content as specified
            if(node_type=="INO_NODE"): # ✅
                if len(content) >= 84:
                    node = UBIFSInoNode.parse(content)
                else:
                    node = UBIFSInoRouteNode.parse(content)

            elif(node_type=="DATA_NODE"): # ✅
                node = UBIFSDataNode.parse(content)

            elif(node_type=="DENT_NODE"): # ✅
                node = UBIFSDentNode.parse(content)

            elif(node_type=="XENT_NODE"): # Not tested
                node = UBIFSXentNode.parse(content)

            elif(node_type=="TRUN_NODE"): # Not tested
                node = UBIFSTrunNode.parse(content)

            elif(node_type=="PAD_NODE"):
                node = UBIFSPadNode.parse(content)
                

            elif(node_type=="SB_NODE"): # ✅
                node = UBIFSSuperblockNode.parse(content)

            elif(node_type=="MST_NODE"): # ✅
                node = UBIFSMasterNode.parse(content)

            elif(node_type=="REF_NODE"): # Not tested
                node = UBIFSRefNode.parse(content)

            elif(node_type=="IDX_NODE"): # error in path(parsing) -> branches -> len
                node = UBIFSIdxNode.parse(content)
                

            elif(node_type=="CS_NODE"):
                # node = UBIFSCsNode.parse(content))
                pass

            elif(node_type=="ORPH_NODE"): # Not tested
                node = UBIFSOrphNode.parse(content)
        else:
            # Payload size is different to that specified
            raise Exception(msg=f"Payload size does not match length of the content ({payload_size} != {len(content)})")
    
    return node
          

def parse_ubifs_image(image_path:str) -> tuple[list[int], list[Struct], list[Struct]]:
    """
    Reads the content of a UBIFS image and returns a tuple containing a list with the offsets of each node, its headers, and its contents.

    Arguments:
        image_path - Path to the UBIFS image file
    """

    nodes:list[Struct] = []
    offsets:list[int] = []
    headers:list[Struct] = []

    with open(image_path, "rb") as f:
        offset = 0
        while True:
            data = f.read(UBIFS_HEADER_SIZE)
            if len(data) < UBIFS_HEADER_SIZE:
                # If there is no more data, exit the "loop"
                break

            try:
                header = UBIFSHeader.parse(data)
            except Exception as e:
                print(f"[0x{offset:X}] Error parsing header: {e}")
                break



            if header.magic != UBIFS_NODE_MAGIC:
                # Invalid magic
                offset += 1
                f.seek(offset)
                continue

            node_type_str = UBIFS_NODE_TYPES.get(header.node_type, "UNKNOWN")
            #print(f"\n0x{offset:06X} - [{node_type_str} ({header.len}B)]")
            body = process_node(node_type_str, header.len - UBIFS_HEADER_SIZE, f)
            if body!=None:
                #print(node)
                nodes.append(body)
                headers.append(header)
                offsets.append(offset)
            
            # print(f"| 0x{offset:06X} | {node_type_str:^9s}({header.node_type:02d}) | {header.len:4d} | {hex(header.crc32):10s} | {hex(header.sqnum):014s} |")
            offset += header.len
        
    return (offsets, headers, nodes)


def node_visualizer(offsets:list[int], headers:list[Struct], nodes:list[Struct]) -> None:
    """
    Function that creates an interactive menu in which the user may explore the content of each node's body and/or header.
    
    Note that the length of the three lists must be the same.
    """
    cont:bool = True
    option:int = 0
    if (len(offsets) != len(headers) or len(headers) != len(nodes) or len(offsets) != len(nodes)):
        raise Exception(msg=f"len(offsets) != len(headers) != len(nodes)\n\t{len(offsets)} != {len(headers)} != {len(nodes)}")
    
    while(cont==True):
        options = {1:"Explore headers",2:"Explore content", 0:"Exit"}
        
        print("Options:")
        for i,j in options.items():
            print(f"\t[{i}]\t{j}")
        
        try:
            option = input("\nSelect one of the options above [0-2]\n")
            option = int(option)
            if (option not in options.keys()):
                print(f"\n\t[{option}] is not a valid option\n")
        except Exception:
            print(f"\n\t[{option}] is not a valid option\n")
            continue

        if(option in options.keys()):
            if option == 0:
                cont = False
            elif option == 1:
                cont_1 = True
                while(cont_1):
                    node=0
                    print("Found nodes:")
                    for i in range(len(nodes)):
                        print(f"\t[{i+1:3d}] - 0x{offsets[i]:06X} : {UBIFS_NODE_TYPES.get(headers[i].node_type, "UNKNOWN"):7} ({headers[i].node_type:02d})")
                    print("\n\t[0] - EXIT")
                    try:
                        node = int(input(f"\nSelect one of the options above [0-{len(nodes)}]\n"))
                        if not (node == 0 or node-1 in range(len(nodes))):
                            print(f"\n\t[{node}] is not a valid option\n")
                    except Exception:
                        print(f"\n\tThat is not a valid option\n")
                        continue
                    if node == 0 or node-1 in range(len(nodes)):
                        if node == 0:
                            cont_1 = False
                        else:
                            print(f"\nContent of the Header of Node #{node} ({UBIFS_NODE_TYPES.get(headers[node-1].node_type, "UNKNOWN"):7} @ 0x{offsets[node-1]:06X}):")
                            for i,j in headers[node-1].items():
                                if i != "_io" and ("padding" not in i):
                                    print(f"\t[{i}]: {j}")
                                elif ("padding" in i):
                                    print(f"\t[{i}]: [...]")

                            input("\n[Press any key to continue...]")
                    
            
            elif option == 2:
                node = 0
                cont_1 = True
                while(cont_1):
                    print("Found nodes:")
                    for i in range(len(nodes)):
                        print(f"\t[{i+1:3d}] - 0x{offsets[i]:06X} : {UBIFS_NODE_TYPES.get(headers[i].node_type, "UNKNOWN"):7} ({headers[i].node_type:02d})")
                    print("\n\t[0] - EXIT")
                    try:
                        node = int(input(f"\nSelect one of the options above [0-{len(nodes)}]\n"))
                        if not (node == 0 or node-1 in range(len(nodes))):
                            print(f"\n\t[{node}] is not a valid option\n")
                    except Exception:
                        print(f"\n\tThat is not a valid option\n")
                        continue
                    if node == 0 or node-1 in range(len(nodes)):
                        if node == 0:
                            cont_1 = False
                        else:
                            print(f"\nContent of the Node #{node} ({UBIFS_NODE_TYPES.get(headers[node-1].node_type, "UNKNOWN"):7} @ 0x{offsets[node-1]:06X}):")
                            for i,j in nodes[node-1].items():
                                if i != "_io" and ("padding" not in i):
                                    print(f"\t[{i}]: {j}")
                                elif ("padding" in i):
                                    print(f"\t[{i}]: [...]")

                            input("\n[Press any key to continue...]")



if __name__ == "__main__":
    (offsets, headers, nodes) = parse_ubifs_image(Path(input("\nPath (relative or absolute) to the UBIFS '.img' file:\n")))
    # (offsets, headers, nodes) = parse_ubifs_image("UBIFS-Explorer\\files.img")
    node_visualizer(offsets, headers, nodes)