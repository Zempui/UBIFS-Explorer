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
| INO_NODE | Inode node | Stores metadata for files and directories. | 
| DATA_NODE | Data node | Contains actual file content. |
| DENT_NODE | Directory entry node | Links filenames to inode numbers. |
| XENT_NODE | Extended attribute node | Stores extended attributes for files. |
| TRUN_NODE | Truncation node | Used to truncate files. |
| PAD_NODE | Padding node | Used to pad unused space in logical erase blocks (LEBs). |
| SB_NODE | Superblock node | Contains filesystem-wide information.
| MST_NODE | Master node | Holds pointers to key filesystem structures.
| REF_NODE | Reference node | Used in the journal to reference other nodes. |
| IDX_NODE | Index node | Part of the indexing structure for fast lookup.
| CS_NODE | Commit start node | Marks the beginning of a commit operation. |
| ORPH_NODE | Orphan node | Tracks inodes that have been deleted but not yet purged (unlinked but still open). |

### File deletion in UBIFS
UBIFS deleted file recovery is challenging but possible by understanding its structure and metadata organization. There are several techniques that may be used for this purspose:
* The first one would be to look for **`ORPH_NODES`** that may reference **recently deleted files**. These nodes may contain the `INODE` numbers of files that were unlinked but that may still have data, which may be cross-referenced with the orphan area of the superblock and may allow to check whether the corresponding `INO_NODES` still exist.
* Another possible technique would be to analyse the **directory entry history**, looking for `DENT_NODES` that may reference `INODES` that are no longer in active directories, checking the *Logical Erase Block* (LEB) garbage collector history, or checking for `DENT_NODES` that may still exist in uncommited aread

The recovery process for each potentially recoverable file would be the following:
TODO: FINISH THIS



## Tools
Several tools have been developed for the current project. In this section, their setup, as well as their usage, will be discussed.

### Setup
In order to install the requirements for these scripts to work:
```bash
python3 -m pip install -r requirements.txt
```

### UBIFS image generator 
The script `ubifs_generator.sh` generated a UBIFS image for the user to test the following scripts on. It may be editted in addition to `ubinize.cfg` to change the image's contents and/or properties.

The script `clean.sh` helps to unmount and eliminate the generated UBIFS image.

### UBIFS image explorer
The script `explorer.py` allows for the parsing of a UBIFS image, allowing the user to get access to all the information stored in the header and body of each node of the image.

Its usage is simple: just execute the script with `python3 explorer.py` and you will be asked to provide the relative or absolute path to the UBIFS `.img` file. Once this is done, a menu with different options will pop up. Navigate the menu by introducing the number of the option you wish to select (i.e. if you want to choose option `[X]`, you will have to enter `X` and press enter), after this, you may choose the node you want to examine following the same steps. To exit the program, just enter the option `0` until you exit every menu.

### UBIFS Filesystem reconstructor

The script `reconstructor.py` reconstructs a filesystem from UBIFS nodes.
It builds directory structures, file metadata, and extracts file contents.

The filesystem reconstruction will follow this logical flow:
```
    INO NODES   → Create file/dir metadata
        ↓
    DENT NODES  → Build directory structure and filename mappings
        ↓
    DATA NODES  → Reconstruct file contents
        ↓
    Final Assembly → Create the actual filesystem on disk
```
Its usage is similar to the `explorer.py` script: just execute the script with `python3 reconstructor.py` and you will be asked to provide the relative or absolute path to the UBIFS `.img` file. After this, the script will automatically parse the file and reconstruct the filesystem in a folder named `reconstructed_fs`.

### Recovery of deleted files (Not implemented)
The recovery of deleted files functionality is not implemented in this repository and is, instead, left as a future improvement to be developed. In this section, however, some guidelines on how to do it are provided:
1. **Extract and Parse the Image**: In order to parse the UBIFS image structure, one can make use of the functions defined in `explorer.py`.
2. **Scan for Orphaned Inodes**: Look for `ORPH_NODES` that reference recently deleted files; These nodes contain inode numbers of files that were unlinked but may still have data. One can cross-reference with the orphan area of the superblock in order to check if the corresponding INO_NODES still exist.
3. **Analyze Directory Entry History**: Scan `DENT_NODES` to find deleted directory entries that reference inodes no longer in active directories. Checking the `LEB` (Logical Erase Block) garbage collection history may reveal deleted `DENT_NODES` that maight still exist in uncommited aread.

4. **Inode Recovery Process**: For each potentially recoverable file:
   * Locate `INO_NODE`: Find the inode metadata node
   * Extract file attributes: Size, timestamps, permissions from `INO_NODE`
   * Find `DATA_NODES`: Locate all data nodes belonging to this inode
   * Reconstruct file: Piece together data nodes in correct order

5. **Raw Data Scanning**: If metadata is corrupted, scan the entire image for `DATA_NODE` signatures, look for file headers/magic numbers in data nodes, and attempt to identify file types by content patterns.



## Known errors / future improvements
* Hard links are not supported
* Symbolic links are no supported in windows systems [WinError 1314]
* Recovery of deleted files is not implemented

## References
[^1]: ["UBIFS - new flash file system" - LWN.net](https://lwn.net/Articles/275706/)

[^2]: ["UBI File System" - docks.kernel.otg](https://docs.kernel.org/5.15/filesystems/ubifs.html)

[^3]: [UBIFS media source code](https://elixir.bootlin.com/linux/v6.15/source/fs/ubifs/ubifs-media.h)