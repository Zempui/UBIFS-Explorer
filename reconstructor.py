from explorer import *
#   The filesystem reconstruction will follow this logical flow:
#       INO NODES   → Create file/dir metadata
#           ↓
#       DENT NODES  → Build directory structure and filename mappings
#           ↓
#       DATA NODES  → Reconstruct file contents
#           ↓
#       Final Assembly → Create the actual filesystem on disk