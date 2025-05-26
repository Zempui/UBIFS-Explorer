// CLI entry point
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define UBIFS_NODE_MAGIC 0x06101831
#define UBIFS_CH_SIZE    24  // common UBIFS node header size

// UBIFS common header (ubifs_ch from Linux kernel)
struct ubifs_ch {
    uint32_t magic;      // must be 0x06101831
    uint8_t  node_type;
    uint8_t  group_type;
    uint16_t padding;
    uint32_t len;
    uint64_t sqnum;
} __attribute__((packed));

// Node type strings for display
const char *node_type_str(uint8_t type) {
    switch (type) {
        case 1: return  "Inode";
        case 2: return  "Data";
        case 3: return  "Direntry";
        case 4: return  "Xattr";
        case 5: return  "Trun";
        case 6: return  "Master";
        case 7: return  "Group";
        case 8: return  "Index";
        default: return "Unknown";
    }
}


int main(int argc, char *argv[]){
    if (argc!=2){
        printf("Usage: %s <ubifs_image>\n", argv[0]);
        return 1;
    }


    FILE *fp = fopen(argv[1],"rb");
    if(!fp){
        perror("Error opening file");
        return 1;
    }

    struct ubifs_ch header;
    size_t offset = 0;

    while(fread(&header, sizeof(header),1,fp) == 1){
        if (header.magic == UBIFS_NODE_MAGIC){
            // Aligned
            printf("Found node at offset 0x%lX: type=%s (%u), len=%u, sqnum=%lu\n",
                offset,
                node_type_str(header.node_type),
                header.node_type,
                header.len,
                header.sqnum);
            
                fseek(fp, header.len - sizeof(header), SEEK_CUR);
                offset += header.len;
        }else{
            // Not aligned, scan byte by byte
            fseek(fp, 1, SEEK_CUR);
            offset += 1;
        }
    }
    fclose(fp);
    return 0;
}
