from construct import Struct, Int32ul, Int8ul, Int64ul, Int16ul, Bytes, Array, Padding, GreedyBytes

# UBIFS constants
UBIFS_NODE_MAGIC = 0x06101831
UBIFS_HEADER_SIZE = 24
UBIFS_KEY_LEN = 16

#############################
#   [STRUCT DECLARATION]    #
#############################

# UBIFS common node header
UBIFSHeader:Struct = Struct(
    "magic" / Int32ul,
    "crc32" / Int32ul,
    "sqnum" / Int64ul,
    "len" / Int32ul,
    "node_type" / Int32ul
)

# 0: INO_NODE
UBIFSInoNode = Struct(
    "inum" / Int64ul,           # Inode number
    "size" / Int64ul,           # File size
    "atime_sec" / Int64ul,      # Access time (seconds)
    "ctime_sec" / Int64ul,      # Change time (seconds)
    "mtime_sec" / Int64ul,      # Modification time (seconds)
    "atime_nsec" / Int32ul,     # Access time (nanoseconds)
    "ctime_nsec" / Int32ul,     # Change time (nanoseconds)
    "mtime_nsec" / Int32ul,     # Modification time (nanoseconds)
    "nlink" / Int32ul,          # Number of hard links
    "uid" / Int32ul,            # User ID
    "gid" / Int32ul,            # Group ID
    "mode" / Int32ul,           # File mode (permissions + type)
    "flags" / Int32ul,          # File flags
    "compr_type" / Int8ul,      # Compression type
    "padding" / Int8ul,         # Padding (usually 0)
    "padding2" / Int16ul,       # More padding to align
    "data" / GreedyBytes   # Remaining is inline data (if any)
)

# 1: DATA_NODE
UBIFSDataNode:Struct = Struct(
    "inode" / Int64ul,
    "size" / Int32ul,
    "compr_type" / Int8ul,
    "encryption_type" / Int8ul,
    "data_size" / Int16ul,
    "data" / Bytes(lambda this: this.data_size)
)

# 2: DENT_NODE
UBIFSDentNode:Struct = Struct(
    "inum" / Int64ul,
    "type" / Int8ul,
    "nlen" / Int8ul,
    "padding" / Int16ul,
    "name_hash" / Int32ul,
    "name" / Bytes(lambda this: this.nlen)
)

# 3: XENT_NODE
UBIFSXentNode:Struct = Struct(
    "inum" / Int64ul,
    "type" / Int8ul,
    "nlen" / Int8ul,
    "padding" / Int16ul,
    "name_hash" / Int32ul,
    "name" / Bytes(lambda this: this.nlen)
)

# 4: TRUN_NODE
UBIFSTrunNode:Struct = Struct(
    "inum" / Int64ul,
    "old_size" / Int64ul,
    "new_size" / Int64ul
)

# 5: PAD_NODE
UBIFSPadNode:Struct = Struct(
    "pad_len" / Int32ul,
    "padding" / GreedyBytes
)

# 6: SB_NODE
UBIFSSuperblockNode:Struct = Struct(
    "key_hash" / Int8ul,
    "key_fmt" / Int8ul,
    "flags" / Int16ul,
    "min_io_size" / Int32ul,
    "leb_size" / Int32ul,
    "leb_cnt" / Int32ul,
    "max_leb_cnt" / Int32ul,
    "log_lebs" / Int32ul,
    "lpt_lebs" / Int32ul,
    "orph_lebs" / Int32ul,
    "jhead_cnt" / Int32ul,
    "fanout" / Int32ul,
    "lsave_cnt" / Int32ul,
    "fmt_version" / Int32ul,
    "default_compr" / Int16ul,
    "padding" / Int16ul,
    "rp_uid" / Int32ul,
    "rp_gid" / Int32ul,
    "rp_size" / Int64ul,
    "time_gran" / Int32ul,
    "uuid" / Bytes(16),
    "label" / Bytes(UBIFS_LABEL_LEN := 128)
)

# 7: MST_NODE
UBIFSMasterNode:Struct = Struct(
    "highest_inum" / Int64ul,
    "cmt_no" / Int64ul,
    "log_lnum" / Int32ul,
    "root_lnum" / Int32ul,
    "root_offs" / Int32ul,
    "root_len" / Int32ul,
    "gc_lnum" / Int32ul,
    "ihead_lnum" / Int32ul,
    "ihead_offs" / Int32ul,
    "index_size" / Int64ul,
    "leb_cnt" / Int32ul,
    "empty_lebs" / Int32ul,
    "idx_lebs" / Int32ul,
    "lpt_lnum" / Int32ul,
    "lpt_offs" / Int32ul,
    "nhead_lnum" / Int32ul,
    "nhead_offs" / Int32ul,
    "ltab_lnum" / Int32ul,
    "ltab_offs" / Int32ul,
    "lsave_lnum" / Int32ul,
    "lsave_offs" / Int32ul,
    "padding" / Bytes(32)
)

# 8: REF_NODE
UBIFSRefNode:Struct = Struct(
    "offs" / Int32ul,
    "lnum" / Int32ul,
    "jhead" / Int8ul,
    "padding" / Padding(7)
)

# Branch used in IDX_NODE
UBIFSBranch:Struct = Struct(
    "key" / Bytes(UBIFS_KEY_LEN),  # key length depends on UBIFS_KEY_LEN, typically 16 bytes
    "lnum" / Int32ul,
    "offs" / Int32ul,
    "len" / Int32ul
)

# 9: IDX_NODE
UBIFSIdxNode:Struct = Struct(
    "child_cnt" / Int16ul,
    "level" / Int16ul,
    "branches" / GreedyBytes # TODO: Differenciate between the branches
)

# 10: CS_NODE
UBIFSCsNode:Struct = Struct(
    "cmt_no" / Int64ul,
    "log_hash" / Bytes(32),  # UBIFS_HASH_LEN is typically 32 (for SHA256)
    "padding" / Bytes(12)    # Depends on alignment and total node size; may need adjustment
)

# 11: ORPH_NODE
UBIFSOrphNode:Struct = Struct(
    "cmt_no" / Int32ul,
    "orph_cnt" / Int32ul,
    "inums" / GreedyBytes # Array(lambda this: this.orph_cnt, Int64ul)
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
                    node = UBIFSUnknownNode.parse(content)

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
          

def parse_ubifs_image(image_path, debug:bool = False) -> tuple[list[int], list[Struct], list[Struct]]:
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
                                if i != "_io":
                                    print(f"\t[{i}]: {j}")

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
                                if i != "_io":
                                    print(f"\t[{i}]: {j}")

                            input("\n[Press any key to continue...]")



if __name__ == "__main__":
    (offsets, headers, nodes) = parse_ubifs_image("UBIFS-Explorer\\files.img", debug=True)
    node_visualizer(offsets, headers, nodes)