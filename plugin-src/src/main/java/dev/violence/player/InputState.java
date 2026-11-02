package dev.violence.player;

import dev.violence.math.Vec3;

/** 플레이어 입력 상태 (클라이언트가 보내는 키 입력/휘두르기/우클릭 패킷 기반). */
public final class InputState {
    public boolean forward, backward, left, right, jump, sneak;
    /** 마지막 왼클릭(휘두르기 패킷) 틱 */
    public long lastSwing = -100;
    /** 이번 틱에 새로 누름이 들어왔는가 */
    public boolean pressedPending;
    public long lastRightClick = -100;
    public long lastJumpPress = -100;

    /** 왼클릭 패킷 수신. 2틱 이상 쉬었다가 들어오면 "새로 누름" */
    public void swing(long now) {
        if (now - lastSwing >= 2) pressedPending = true;
        lastSwing = now;
    }

    /** 누르고 있는 중인가: 블록을 조준한 채 누르면 클라이언트가 매 틱 휘두르기 패킷을 보낸다 */
    public boolean held(long now) {
        return now - lastSwing <= 1;
    }

    public boolean consumePressed() {
        boolean p = pressedPending;
        pressedPending = false;
        return p;
    }

    /**
     * 우클릭: 꾹 누르고 있으면 클라이언트가 4틱마다 반복해서 보내므로
     * 5틱 넘게 쉬었다 들어온 것만 새 입력으로 본다.
     */
    public boolean rightClick(long now) {
        boolean fresh = now - lastRightClick > 5;
        lastRightClick = now;
        return fresh;
    }

    public Vec3 moveDirection(Vec3 look) {
        Vec3 f = look.horizontal().normalize();
        Vec3 r = new Vec3(-f.z(), 0, f.x());
        Vec3 m = Vec3.ZERO;
        if (forward) m = m.add(f);
        if (backward) m = m.sub(f);
        if (right) m = m.add(r);
        if (left) m = m.sub(r);
        return m.normalize();
    }

    public void reset() {
        pressedPending = false;
        lastSwing = -100;
    }
}
