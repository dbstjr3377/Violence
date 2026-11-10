package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import dev.violence.pack.SkinPack;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.jupiter.api.Test;

/** 1인칭 팔 스킨 팩: 어떤 스킨이든 64x64 표준(팔 4픽셀) 배치로 바뀌는지 */
class SkinPackTest {
    private static final int FRONT = 0xFF112233, BACK = 0xFF445566, OUTER = 0xFF778899;

    @Test
    void slimArmIsWidenedToFourPixels() {
        BufferedImage in = new BufferedImage(64, 64, BufferedImage.TYPE_INT_ARGB);
        // 얇은 오른팔: 바깥 40~43, 앞 44~46, 안 47~50, 뒤 51~53
        for (int y = 20; y < 32; y++) {
            for (int x = 40; x < 44; x++) in.setRGB(x, y, OUTER);
            for (int x = 44; x < 47; x++) in.setRGB(x, y, FRONT);
            for (int x = 51; x < 54; x++) in.setRGB(x, y, BACK);
        }
        BufferedImage out = SkinPack.normalize(in, true);
        for (int x = 44; x < 48; x++) assertEquals(FRONT, out.getRGB(x, 25), "앞면 4픽셀");
        for (int x = 52; x < 56; x++) assertEquals(BACK, out.getRGB(x, 25), "뒷면 4픽셀");
        assertEquals(OUTER, out.getRGB(40, 25));
    }

    @Test
    void legacySkinGetsMirroredLeftArm() {
        BufferedImage in = new BufferedImage(64, 32, BufferedImage.TYPE_INT_ARGB);
        for (int y = 20; y < 32; y++) for (int x = 44; x < 48; x++) in.setRGB(x, y, FRONT);
        BufferedImage out = SkinPack.normalize(in, false);
        assertEquals(64, out.getHeight());
        // 왼팔 앞면 (36~39, 52~63)
        assertEquals(FRONT, out.getRGB(37, 56));
    }

    @Test
    void hiResSkinIsDownscaled() throws Exception {
        BufferedImage in = new BufferedImage(128, 128, BufferedImage.TYPE_INT_ARGB);
        in.setRGB(88, 40, FRONT);   // (44,20) 의 2배 자리
        assertEquals(FRONT, SkinPack.normalize(in, false).getRGB(44, 20));
        // 팩 만들기: pack.mcmeta 를 본 팩에서 가져옴
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream z = new ZipOutputStream(bos)) {
            z.putNextEntry(new ZipEntry("pack.mcmeta"));
            z.write("{\"pack\":{}}".getBytes());
            z.closeEntry();
        }
        assertNotNull(SkinPack.build(bos.toByteArray(), SkinPack.normalize(in, false)));
    }
}
