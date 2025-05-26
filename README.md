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


## Refferences
[^1]: ["UBIFS - new flash file system" - LWN.net](https://lwn.net/Articles/275706/)

[^2]: ["UBI File System" - docks.kernel.otg](https://docs.kernel.org/5.15/filesystems/ubifs.html)