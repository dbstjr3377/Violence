package dev.violence.fx;

import org.bukkit.entity.ItemDisplay;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3d;
import org.joml.Vector3f;

/**
 * 넘어짐·처형 인형에 실제 스킨을 입힘.
 *
 * 인형 부위마다 그 사람의 프로필을 가진 플레이어 머리(아이템 디스플레이)를 부위 크기로 늘려 놓는다.
 * 머리 모델은 스킨의 머리 부분만 쓰므로, 리소스팩 entity 쉐이더가 부위에 맞는 스킨 영역(몸통·팔·다리)으로 UV 를 바꿔 그린다.
 * 쉐이더가 부위를 알 수 있게 디스플레이 밝기를 (블록 15, 하늘 = 부위 번호 1~10) 으로 둔다.
 * 실제 개체는 자기 자리의 블록 밝기가 15일 수 없다(경기장의 빛 블록은 꽉 찬 블록이거나 천장에 매단 랜턴).
 * 그래서 entity 쉐이더에서 이 조합은 인형뿐이고, 쉐이더가 인형을 보통 실내 밝기로 다시 비춘다.
 */
public final class SkinPuppet {
    private SkinPuppet() {}

    /** 플레이어 머리 모델: 0.5 블록 정육면체, 아이템 디스플레이(NONE) 원점에서 중심이 0.25 블록 아래 */
    static final float HEAD_CUBE = 0.5f;
    static final float HEAD_CENTER_Y = -0.25f;
    /** 머리 모델의 얼굴 방향을 인형 부위의 앞쪽에 맞추는 회전 */
    static final Quaternionf ORIENT = new Quaternionf().rotateY((float) Math.PI);

    /** 쉐이더 부위 번호 (tools/shaders/include/violence_skin.glsl 과 같아야 함) */
    public static int code(FallPose.Part part) {
        return switch (part) {
            case HEAD -> 1;
            case BODY -> 2;
            case ARM_R -> 3;
            case FOREARM_R -> 4;
            case ARM_L -> 5;
            case FOREARM_L -> 6;
            case LEG_R -> 7;
            case SHIN_R -> 8;
            case LEG_L -> 9;
            case SHIN_L -> 10;
        };
    }

    /** 머리 정육면체를 부위 상자(중심 c, 회전 r, 크기 = 부위 픽셀 × 플레이어 비율)로 */
    public static Transformation transform(FallPose.Part part, Vector3d c, Quaternionf r, double scale) {
        float sx = (float) (part.size.x * FallPose.PX * scale / HEAD_CUBE);
        float sy = (float) (part.size.y * FallPose.PX * scale / HEAD_CUBE);
        float sz = (float) (part.size.z * FallPose.PX * scale / HEAD_CUBE);
        Vector3f off = r.transform(new Vector3f(0, HEAD_CENTER_Y * sy, 0));
        Vector3f t = new Vector3f((float) c.x, (float) c.y, (float) c.z).sub(off);
        return new Transformation(t, new Quaternionf(r), new Vector3f(sx, sy, sz), new Quaternionf(ORIENT));
    }

    public static void mark(ItemDisplay d, FallPose.Part part) {
        d.setBrightness(new org.bukkit.entity.Display.Brightness(15, code(part)));
    }
}
