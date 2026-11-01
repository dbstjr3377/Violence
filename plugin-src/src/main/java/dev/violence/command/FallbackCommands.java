package dev.violence.command;

import dev.violence.ViolencePlugin;
import java.util.List;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

/** Skript 가 설치되지 않았을 때 /게임시작, /게임중단 을 플러그인이 직접 등록한다. */
public final class FallbackCommands {
    private FallbackCommands() {}

    public static void registerIfNeeded(ViolencePlugin plugin) {
        if (Bukkit.getPluginManager().isPluginEnabled("Skript") && Bukkit.getCommandMap().getCommand("게임시작") != null) return;
        if (Bukkit.getCommandMap().getCommand("게임시작") != null) return;
        Bukkit.getCommandMap().register("violence", new Command("게임시작", "게임을 시작합니다", "/게임시작 [맵] [목표킬] [제한시간(초)]", List.of()) {
            @Override
            public boolean execute(CommandSender sender, String label, String[] args) {
                if (!sender.hasPermission("violence.admin")) return true;
                int kills = args.length > 1 ? parse(args[1]) : -1;
                int secs = args.length > 2 ? parse(args[2]) : -1;
                plugin.game().start(sender, args.length > 0 ? args[0] : null, -1, kills, secs);
                return true;
            }
        });
        Bukkit.getCommandMap().register("violence", new Command("게임중단", "게임을 중단합니다", "/게임중단", List.of()) {
            @Override
            public boolean execute(CommandSender sender, String label, String[] args) {
                if (!sender.hasPermission("violence.admin")) return true;
                plugin.game().stop(sender);
                return true;
            }
        });
        for (Player p : Bukkit.getOnlinePlayers()) p.updateCommands();
        plugin.getLogger().info("Skript 가 없어 /게임시작, /게임중단 을 플러그인이 직접 등록했습니다.");
    }

    private static int parse(String s) {
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
