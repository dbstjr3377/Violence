package dev.violence.pack;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;
import javax.imageio.ImageIO;

/**
 * 1인칭 팔 스킨 리소스팩 (순수 계산이라 서버 없이 테스트 가능).
 * 리소스팩의 1인칭 무기 모델은 팔에 violence:skin/self 텍스처(64x64 표준 스킨 배치)를 쓴다.
 * 플레이어마다 자기 스킨을 그 경로에 넣은 작은 팩을 따로 보내 덮으므로, 같은 모델로 각자 자기 팔이 보인다.
 */
public final class SkinPack {
    private SkinPack() {}

    public static final String TEXTURE_PATH = "assets/violence/textures/skin/self.png";

    /**
     * 어떤 스킨이든 64x64 표준(팔 4픽셀) 배치로 바꿈.
     *  - 64x32 옛 스킨: 아래 절반(왼팔·왼다리)을 오른쪽 것을 좌우 뒤집어 채움
     *  - 얇은 팔(Alex, 3픽셀): 팔의 앞/뒤/위/아래 면을 4픽셀로 늘림
     */
    public static BufferedImage normalize(BufferedImage in, boolean slim) {
        int scale = Math.max(1, in.getWidth() / 64);
        BufferedImage src = new BufferedImage(64, in.getHeight() / scale, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < src.getHeight(); y++)
            for (int x = 0; x < 64; x++) src.setRGB(x, y, in.getRGB(x * scale, y * scale));
        BufferedImage out = new BufferedImage(64, 64, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < Math.min(64, src.getHeight()); y++)
            for (int x = 0; x < 64; x++) out.setRGB(x, y, src.getRGB(x, y));
        if (src.getHeight() < 64) {
            // 옛 스킨: 왼팔 = 오른팔 거울, 왼다리 = 오른다리 거울 (겉옷 층은 비움)
            mirrorLimb(out, 40, 16, 32, 48);
            mirrorLimb(out, 0, 16, 16, 48);
        }
        if (slim) {
            for (int[] o : new int[][]{{40, 16}, {40, 32}, {32, 48}, {48, 48}}) widenArm(out, o[0], o[1]);
        }
        return out;
    }

    /** 팔다리 한 칸(16x16 영역)을 좌우로 뒤집어 다른 자리로 복사 (옛 스킨의 왼쪽 팔다리) */
    private static void mirrorLimb(BufferedImage img, int sx, int sy, int dx, int dy) {
        // 위·아래 면 (4x4 두 개)
        for (int y = 0; y < 4; y++)
            for (int x = 0; x < 4; x++) {
                img.setRGB(dx + 4 + x, dy + y, img.getRGB(sx + 4 + 3 - x, sy + y));
                img.setRGB(dx + 8 + x, dy + y, img.getRGB(sx + 8 + 3 - x, sy + y));
            }
        // 옆면 띠 (바깥 ↔ 안쪽이 바뀌고 각 면이 뒤집힘)
        int[] order = {8, 4, 0, 12};
        for (int i = 0; i < 4; i++) {
            int from = sx + order[i];
            int to = dx + i * 4;
            for (int y = 0; y < 12; y++)
                for (int x = 0; x < 4; x++) img.setRGB(to + x, dy + 4 + y, img.getRGB(from + 3 - x, sy + 4 + y));
        }
    }

    /** 얇은 팔(가로 3픽셀) 한 칸을 4픽셀 배치로 늘림. (u,v) = 팔 영역 왼쪽 위 */
    private static void widenArm(BufferedImage img, int u, int v) {
        int[][] region = new int[16][16];
        for (int y = 0; y < 16; y++)
            for (int x = 0; x < 16; x++) region[y][x] = img.getRGB(u + x, v + y);
        for (int y = 0; y < 16; y++)
            for (int x = 0; x < 16; x++) img.setRGB(u + x, v + y, 0);
        // 위(3x4) → 4x4, 아래(3x4) → 4x4
        stretch(img, region, 4, 0, 3, 4, u + 4, v);
        stretch(img, region, 7, 0, 3, 4, u + 8, v);
        // 옆면: 바깥(4) | 앞(3) | 안(4) | 뒤(3) → 4 | 4 | 4 | 4
        stretch(img, region, 0, 4, 4, 12, u, v + 4);
        stretch(img, region, 4, 4, 3, 12, u + 4, v + 4);
        stretch(img, region, 7, 4, 4, 12, u + 8, v + 4);
        stretch(img, region, 11, 4, 3, 12, u + 12, v + 4);
    }

    private static void stretch(BufferedImage img, int[][] region, int rx, int ry, int w, int h, int dx, int dy) {
        for (int y = 0; y < h; y++)
            for (int x = 0; x < 4; x++) img.setRGB(dx + x, dy + y, region[ry + y][rx + Math.min(w - 1, x * w / 4)]);
    }

    /** 스킨 팩 zip: 본 리소스팩의 pack.mcmeta + 스킨 텍스처 */
    public static byte[] build(byte[] mainPackZip, BufferedImage skin) throws IOException {
        byte[] mcmeta = entry(mainPackZip, "pack.mcmeta");
        if (mcmeta == null) throw new IOException("리소스팩에 pack.mcmeta 가 없음");
        ByteArrayOutputStream png = new ByteArrayOutputStream();
        ImageIO.write(skin, "png", png);
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            zos.putNextEntry(new ZipEntry("pack.mcmeta"));
            zos.write(mcmeta);
            zos.closeEntry();
            zos.putNextEntry(new ZipEntry(TEXTURE_PATH));
            zos.write(png.toByteArray());
            zos.closeEntry();
        }
        return bos.toByteArray();
    }

    static byte[] entry(byte[] zip, String name) throws IOException {
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e;
            while ((e = zis.getNextEntry()) != null) {
                if (e.getName().equals(name)) return zis.readAllBytes();
            }
        }
        return null;
    }
}
