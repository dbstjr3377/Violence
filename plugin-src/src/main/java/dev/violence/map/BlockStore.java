package dev.violence.map;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.data.BlockData;

/**
 * 맵 블록 저장 형식 (blocks.vmap, gzip).
 * 월드 폴더를 복사하지 않고 블록 상태 문자열 팔레트 + 인덱스로 저장하므로
 * 서버 버전의 월드 저장 구조가 바뀌어도 그대로 쓸 수 있다.
 */
public final class BlockStore {
    private static final int MAGIC = 0x564D4150; // "VMAP"
    private static final int VERSION = 1;

    public final int ox, oy, oz, sx, sy, sz;
    public final List<String> palette;
    public final int[] data;

    public BlockStore(int ox, int oy, int oz, int sx, int sy, int sz, List<String> palette, int[] data) {
        this.ox = ox; this.oy = oy; this.oz = oz;
        this.sx = sx; this.sy = sy; this.sz = sz;
        this.palette = palette;
        this.data = data;
    }

    private int index(int x, int y, int z) { return (y * sz + z) * sx + x; }

    /** 월드에서 영역을 읽는다 (메인 스레드). */
    public static BlockStore capture(World w, int minX, int minY, int minZ, int maxX, int maxY, int maxZ) {
        int sx = maxX - minX + 1, sy = maxY - minY + 1, sz = maxZ - minZ + 1;
        List<String> palette = new ArrayList<>();
        Map<String, Integer> idx = new HashMap<>();
        palette.add("minecraft:air");
        idx.put("minecraft:air", 0);
        int[] data = new int[sx * sy * sz];
        for (int y = 0; y < sy; y++) {
            for (int z = 0; z < sz; z++) {
                for (int x = 0; x < sx; x++) {
                    var b = w.getBlockAt(minX + x, minY + y, minZ + z);
                    if (b.getType().isAir() || b.getType() == Material.BARRIER) continue;
                    String s = b.getBlockData().getAsString();
                    Integer i = idx.get(s);
                    if (i == null) {
                        i = palette.size();
                        palette.add(s);
                        idx.put(s, i);
                    }
                    data[(y * sz + z) * sx + x] = i;
                }
            }
        }
        return new BlockStore(minX, minY, minZ, sx, sy, sz, palette, data);
    }

    public void save(File f) throws IOException {
        f.getParentFile().mkdirs();
        try (DataOutputStream out = new DataOutputStream(new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(f))))) {
            out.writeInt(MAGIC);
            out.writeInt(VERSION);
            out.writeInt(ox); out.writeInt(oy); out.writeInt(oz);
            out.writeInt(sx); out.writeInt(sy); out.writeInt(sz);
            out.writeInt(palette.size());
            for (String s : palette) out.writeUTF(s);
            // 런 렝스 인코딩 (공기가 대부분이라 효율적)
            int i = 0;
            while (i < data.length) {
                int v = data[i];
                int run = 1;
                while (i + run < data.length && data[i + run] == v && run < 65535) run++;
                writeVar(out, v);
                writeVar(out, run);
                i += run;
            }
        }
    }

    public static BlockStore load(File f) throws IOException {
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(f))))) {
            if (in.readInt() != MAGIC) throw new IOException("올바른 맵 파일이 아닙니다: " + f);
            int ver = in.readInt();
            if (ver != VERSION) throw new IOException("지원하지 않는 맵 파일 버전: " + ver);
            int ox = in.readInt(), oy = in.readInt(), oz = in.readInt();
            int sx = in.readInt(), sy = in.readInt(), sz = in.readInt();
            int n = in.readInt();
            List<String> palette = new ArrayList<>(n);
            for (int i = 0; i < n; i++) palette.add(in.readUTF());
            int[] data = new int[sx * sy * sz];
            int i = 0;
            while (i < data.length) {
                int v = readVar(in);
                int run = readVar(in);
                for (int k = 0; k < run && i < data.length; k++) data[i++] = v;
            }
            return new BlockStore(ox, oy, oz, sx, sy, sz, palette, data);
        }
    }

    private static void writeVar(DataOutputStream out, int v) throws IOException {
        while ((v & ~0x7F) != 0) {
            out.writeByte((v & 0x7F) | 0x80);
            v >>>= 7;
        }
        out.writeByte(v);
    }

    private static int readVar(DataInputStream in) throws IOException {
        int v = 0, shift = 0;
        while (true) {
            int b = in.readUnsignedByte();
            v |= (b & 0x7F) << shift;
            if ((b & 0x80) == 0) return v;
            shift += 7;
        }
    }

    /** 팔레트를 BlockData 로 변환 (알 수 없는 블록은 돌로 대체) */
    public BlockData[] resolvePalette() {
        BlockData[] out = new BlockData[palette.size()];
        for (int i = 0; i < out.length; i++) {
            try {
                out[i] = Bukkit.createBlockData(palette.get(i));
            } catch (IllegalArgumentException e) {
                out[i] = Material.STONE.createBlockData();
            }
        }
        return out;
    }

    public int get(int x, int y, int z) { return data[index(x, y, z)]; }
    public int volume() { return data.length; }
}
