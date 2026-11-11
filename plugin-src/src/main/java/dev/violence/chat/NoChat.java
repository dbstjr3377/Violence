package dev.violence.chat;

import dev.violence.ViolencePlugin;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.Bukkit;
import org.bukkit.GameRules;
import org.bukkit.World;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerAdvancementDoneEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerKickEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.world.WorldLoadEvent;

/**
 * 시스템 채팅을 쓰지 않는다 (화면에 채팅 줄이 뜨지 않게).
 *  - 바닐라: 명령 결과("Teleported ..."), 콘솔 명령 알림("[Server: ...]"), 접속·퇴장·사망·발전과제 메시지를 모든 월드에서 끔
 *  - 이 플러그인과 Skript 의 알림은 채팅 대신 서버 콘솔에 남김
 *  - 관리자 명령의 결과는 콘솔에, 게임 중이 아닌 관리자에게는 액션바로만 보여 줌
 * 플레이어끼리 하는 채팅은 그대로 둔다.
 */
public final class NoChat implements Listener {
    private static ViolencePlugin plugin;

    public NoChat(ViolencePlugin p) {
        plugin = p;
        for (World w : Bukkit.getWorlds()) quiet(w);
    }

    /** 월드의 바닐라 시스템 메시지를 모두 끔 */
    public static void quiet(World w) {
        w.setGameRule(GameRules.SEND_COMMAND_FEEDBACK, false);
        w.setGameRule(GameRules.LOG_ADMIN_COMMANDS, false);
        w.setGameRule(GameRules.COMMAND_BLOCK_OUTPUT, false);
        w.setGameRule(GameRules.SHOW_DEATH_MESSAGES, false);
        w.setGameRule(GameRules.SHOW_ADVANCEMENT_MESSAGES, false);
    }

    @EventHandler
    public void onWorldLoad(WorldLoadEvent e) {
        quiet(e.getWorld());
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onJoin(PlayerJoinEvent e) {
        e.joinMessage(null);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onQuit(PlayerQuitEvent e) {
        e.quitMessage(null);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onKick(PlayerKickEvent e) {
        e.leaveMessage(Component.empty());
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onDeath(PlayerDeathEvent e) {
        e.deathMessage(null);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onAdvancement(PlayerAdvancementDoneEvent e) {
        e.message(null);
    }

    /** 알림: 채팅 대신 서버 콘솔에 */
    public static void log(Component c) {
        if (plugin != null) plugin.getLogger().info(plain(c));
    }

    public static void log(String s) {
        if (plugin != null) plugin.getLogger().info(s);
    }

    /** 명령 결과: 콘솔이면 그대로, 플레이어면 콘솔에 남기고 게임 밖에서는 액션바로만 */
    public static void tell(CommandSender s, Component c) {
        if (!(s instanceof Player p)) {
            s.sendMessage(c);
            return;
        }
        log("[" + p.getName() + "] " + plain(c));
        boolean inGame = plugin != null && plugin.arena() != null && plugin.arena().players.containsKey(p.getUniqueId());
        if (!inGame) p.sendActionBar(c);
    }

    private static String plain(Component c) {
        return PlainTextComponentSerializer.plainText().serialize(c);
    }
}
