from construct import Struct, Int32ul, Int8ul, Int64ul, Int16ul
import sys

# UBIFS constants
UBIFS_NODE_MAGIC = 0x06101831
UBIFS_HEADER_SIZE = 24

# UBIFS common node header
UBIFSHeader:Struct = Struct(
    "magic" / Int32ul,
    "crc32" / Int32ul,
    "sqnum" / Int64ul,
    "len" / Int32ul,
    "node_type" / Int32ul
)

# Mapping of node types (partial list from UBIFS source)
UBIFS_NODE_TYPES = {
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


def parse_ubifs_image(image_path, debug:bool = False):
    with open(image_path, "rb") as f:
        offset = 0
        print("|  offset  | node type (n) | len  |   crc 32   |   seq number   |\n|==========|===============|======|============|================|")
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


            # Skip payload
            f.seek(header.len - UBIFS_HEADER_SIZE, 1) # type: ignore
            # if(input(f"| 0x{offset:06X} | {node_type_str:^9s}({header.node_type:02d}) | {header.len:4d} | {hex(header.crc32):10s} | {hex(header.sqnum):014s} |")!=''):
            #     break
            print(f"| 0x{offset:06X} | {node_type_str:^9s}({header.node_type:02d}) | {header.len:4d} | {hex(header.crc32):10s} | {hex(header.sqnum):014s} |")
            offset += header.len
        

if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print("Usage: python ubifs_parser.py <ubifs_image>")
    #     sys.exit(1)

    # parse_ubifs_image(sys.argv[1])
    parse_ubifs_image("UBIFS-Explorer\\files.img", debug=True)