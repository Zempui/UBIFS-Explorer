# UBIFS-Explorer

This project is part of the *Cyber-crime and Computer Forensics* course at EURECOM's Digital Security track.

## The task:
>There are a number of filesystems that are commonly used in embedded devices.
>
>Some (like FAT) are also common elsewhere and are supported by forensic tools. Other (like LittleFS, SPIFFS, Yaffs, UBIFS...) are not.
>
>Pick one and study it. Then write a couple of paragraphs to say where it is used, what are its main characteristics, and what happens when you delete a file in terms of core data structure. 
>
>Then try to write a little forensic tool that can list the files and directories, print its core data-structure information, and (if possible) recover deleted files.

## UBIFS

Unsorted Block Image File System (**UBIFS**) is a flash system developed by Nokia engineers with help of the University of Szeged. It is a flash file system for unmanaged flash memory devices. It works on top of UBI (unsorted block image), which is a separate software layer which may be found in *drivers/mtd/ubi*.  UBI is basically a volume management and wear-leveling layer. It provides so called UBI volumes which is a higher level abstraction than a MTD device.[^1] [^2]

UBIFS can be considered a next generation of the JFFS2 file-system, although it is incompatible with it due to its differences:
* While JFFS2 works on top of MTD devices, UBIFS works on top of UBI volumes.
* JFFS2 does not have on-media index and has to build it while mounting, which requires a full media scan. UBIFS, on the other hand, keeps the FS indexing information on the flash media, without the need for a full media scan, resulting in faster mounting times than JFFS2.
* JFFS2 is a write-through file system, while UBIFS supports write-back, shortening writing times drastically.
* UBIFS scales logarithmically, so the mount time and memory consumption do not linearly depend on the flash size, like in the case of JFFS2 (UBI/UBIFS scales considerably better).

However, there are also some similarities with JFFS2:
* Both JFFS2 and UBIFS support on-the-flight compression which makes it possible to fit great amounts of data on the flash.
* Both are tolerant to unclean reboots and power-cuts. UBIFS automatically replays its journal and recovers from crashes, ensuring that the on-flash data structures are consistent.

### UBIFS Nodes
UBIFS uses different types of nodes, such as data nodes that store fragments of file content or inode nodes. The main types are: [^3]
| Name | Meaning | Description |
|------|---------|-------------|
| INO_NODE | Inode node | stores metadata for files and directories. | 
| DATA_NODE | Data node | contains actual file content. |
| DENT_NODE | Directory entry node | links filenames to inode numbers. |
| XENT_NODE | Extended attribute node | stores extended attributes for files. |
| TRUN_NODE | Truncation node | used to truncate files. |
| PAD_NODE | Padding node | used to pad unused space in logical erase blocks (LEBs). |
| SB_NODE | Superblock node | contains filesystem-wide information.
| MST_NODE | Master node | holds pointers to key filesystem structures.
| REF_NODE | Reference node | used in the journal to reference other nodes. |
| IDX_NODE | Index node | part of the indexing structure for fast lookup.
| CS_NODE | Commit start node | marks the beginning of a commit operation. |
| ORPH_NODE | Orphan node | tracks inodes that have been deleted but not yet purged. |

## Tools
Several tools have been developed for the current project. In this section, their setup, as well as their usage, will be discussed.

### Setup
In order to install the requirements for these scripts to work:
```bash
python3 -m pip install -r requirements.txt
```

### UBIFS image explorer
The script `explorer.py` allows for the parsing of a UBIFS image, allowing the user to get access to all the information stored in the header and body of each node of the image.

Its usage is simple: just execute the script with `python3 explorer.py` and you will be asked to provide the relative or absolute path to the UBIFS `.img` file. Once this is done, a menu with different options will pop up. Navigate the menu by introducing the number of the option you wish to select (i.e. if you want to choose option `[X]`, you will have to enter `X` and press enter), after this, you may choose the node you want to examine following the same steps. To exit the program, just enter the option `0` until you exit every menu.

### UBIFS Filesystem reconstructor

The script `reconstructor.py` reconstructs a filesystem from UBIFS nodes.
It builds directory structures, file metadata, and extracts file contents.

The filesystem reconstruction will follow this logical flow:
    INO NODES   → Create file/dir metadata
        ↓
    DENT NODES  → Build directory structure and filename mappings
        ↓
    DATA NODES  → Reconstruct file contents
        ↓
    Final Assembly → Create the actual filesystem on disk

Its usage is similar to the `explorer.py` script: just execute the script with `python3 reconstructor.py` and you will be asked to provide the relative or absolute path to the UBIFS `.img` file. After this, the script will automatically parse the file and reconstruct the filesystem in a folder named `reconstructed_fs`.

## Known errors / future improvements
* Hard links are not supported
* Symbolic links are no supported in windows systems [WinError 1314]

## References
[^1]: ["UBIFS - new flash file system" - LWN.net](https://lwn.net/Articles/275706/)

[^2]: ["UBI File System" - docks.kernel.otg](https://docs.kernel.org/5.15/filesystems/ubifs.html)

[^3]: [UBIFS media source code](https://elixir.bootlin.com/linux/v6.15/source/fs/ubifs/ubifs-media.h)