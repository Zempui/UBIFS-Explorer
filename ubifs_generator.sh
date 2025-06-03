#!/bin/bash
if [ ! -d files ]; then 
	# Make the content
	echo "Generating root content.."
	mkdir files
	echo "$(date)" > files/date.txt
	echo "Another content" > files/other.txt
	mkdir files/folder
	echo "This file is in a folder" > files/folder/folder.txt
	ln files/folder/folder.txt hard_link
	ln -s files/folder/folder.txt soft_link
	echo "This file was removed" > files/removed.txt
	rn files/removed.txt

fi

if [ ! -f ubinize.cfg ]; then
	echo "Generating ubinize config.."
	cat <<END > ubinize.cfg
[ubi_rfs]
mode=ubi
image=files.img
vol_id=0
vol_size=10MiB
vol_type=dynamic
vol_name=testfs
vol_flags=autoresize
END
fi

echo "Creating test.img volume from 'files' directory.."
mkfs.ubifs -q -r files -m 2048 -e 129024 -c 100 -o files.img

echo "Creating UBI Image as ubi.img contain 1 volume (files.img).."
ubinize -o ubi.img -m 2048 -p 128KiB -s 512 ubinize.cfg

# -r root-fs: tells mkfs.ubifs to create an UBIFS image which would have identical contents as the local root-fs directory;
# -m 2048: tells mkfs.ubifs that the minimum input/output unit size of the flash this UBIFS image is created for is 2048 bytes (NAND page in this case);
# -e 129024: logical eraseblock size of the UBI volume this image is created for;
# -c 2047: specifies maximum file-system size in logical eraseblocks; this means that it will be possible to use the resulting file-system on volumes up to this size (less or equivalent); so in this particular case, the resulting FS may be put on volumes up to about 251MiB (129024 multiplied by 2047); See this section for more details.
# -p 128KiB: tells ubinize that physical eraseblock size of the flash chip the UBI image is created for is 128KiB (128 * 1024 bytes);
# -s 512: tells ubinize that the flash supports sub-pages and sub-page size is 512 bytes; ubinize will take this into account and put the VID header to the same NAND page as the EC header.

if [ ! -f files.img ]; then
	echo "Something wrong.."
	exit 1
fi
if [ ! -f ubi.img ]; then
	echo "Something wrong.."
	exit 1
fi

# Load UBI module

echo "Prepare the NAND Emulator for MTD devices.."
# https://stackoverflow.com/questions/24056437/how-to-mount-ubifs-filesystem-on-android-emulator
# nandsim emulating Micron 3.3V 256MiB, 2048 bytes page.
sudo modprobe nandsim first_id_byte=0x2c second_id_byte=0xda third_id_byte=0x90 fourth_id_byte=0x95

if [ ! -c /dev/mtd0 ]; then
	echo "Something wrong with nandsim kernel module, mtd block not created."
	exit
fi

sudo modprobe ubi
sudo modprobe mtd

echo "Formating mtd0 and fill with ubi.img.."
sudo ubiformat /dev/mtd0 -f ubi.img

echo "Attach ubi to mtd0.. creating /dev/ubi0"
sudo ubiattach -p /dev/mtd0

echo "Mount /dev/ubi0_0"
[ -d mount ] || mkdir mount
sudo mount -t ubifs /dev/ubi0_0 ./mount

if [ "$?" -eq "0" ]; then
	echo "Files should be mounted on $PWD/mount"
else
	echo "Mount failed"
fi

if [ ! -f clean.sh ]; then
	cat <<END > clean.sh
#!/bin/bash
# CLEAN or unmount script:
sudo umount ./mount
rmdir ./mount
sudo ubidetach -p /dev/mtd0
sudo modprobe -a -r ubifs ubi nandsim mtdblock mtd
# deleted if required
#unlink files.img ubi.img
END
chmod +x clean.sh
fi
