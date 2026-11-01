package dev.violence.game;

import dev.violence.ViolencePlugin;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;

/**
 * Skript 연동. 게임 규칙 일부(점수표, 콤보 공식, 알림 메시지)를 Skript 가 담당한다.
 * 자바 → Skript: 콘솔로 "/vhook <이벤트> ..." 실행 (Skript 스크립트가 정의한 명령어)
 * Skript → 자바: 스크립트가 "/violence award|combobonus ..." 실행
 * Skript 가 없거나 응답하지 않으면 config.yml 의 기본값을 쓴다.
 */
public final class SkriptBridge {
    private final ViolencePlugin plugin;

    public SkriptBridge(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public boolean available() {
        if (!plugin.getConfig().getBoolean("skript.enabled", true)) return false;
        if (!Bukkit.getPluginManager().isPluginEnabled("Skript")) return false;
        Command c = Bukkit.getCommandMap().getCommand("vhook");
        return c != null;
    }

    /** Skript 훅 호출. 성공 여부 반환. */
    public boolean call(String event, Object... args) {
        if (!available()) return false;
        StringBuilder sb = new StringBuilder("vhook ").append(event);
        for (Object a : args) sb.append(' ').append(String.valueOf(a).replace(' ', '_'));
        try {
            return Bukkit.dispatchCommand(Bukkit.getConsoleSender(), sb.toString());
        } catch (RuntimeException e) {
            plugin.getLogger().warning("Skript 훅 실패 (" + event + "): " + e);
            return false;
        }
    }
}
