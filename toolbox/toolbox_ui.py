#!/usr/bin/env python3
"""DreamerCG Batocera Toolbox: controller and keyboard friendly installer menu."""
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Pygame est requis (Batocera l’inclut généralement avec Python).", file=sys.stderr)
    raise SystemExit(1)


INSTALLERS = [
    {
        "name": "Linux Loader",
        "author": "By DreamerCG",
        "tag": "ARCADE · TEKNOPARROT",
        "description": [
            "Installe Linux Loader et ses fichiers système.",
            "Ajoute les réglages TeknoParrot.",
            "Fusionne les fichiers existants.",
        ],
        "command": "curl -Ls https://raw.githubusercontent.com/DreamerCG/linuxloader/main/install.sh | bash",
        "warning": "La sortie et les éventuelles questions de l’installateur s’affichent dans le terminal.",
    },
    {
        "name": "Toolbox Switch",
        "author": "By DreamerCG",
        "tag": "NINTENDO SWITCH",
        "description": [
            "Installe ou actualise la toolbox Switch.",
            "Prend en charge Batocera 41 à 44.",
            "EmulationStation redémarre à la fin.",
        ],
        "command": "curl -k -sL https://dreamercg.s.gy/switch | bash",
        "warning": "La sortie et les éventuelles questions de l’installateur s’affichent dans le terminal.",
    },
    {
        "name": "Ultimate Wine Toolbox",
        "author": "By Thomsonito",
        "tag": "WINE · WINDOWS GAMES",
        "description": [
            "Lance l’installateur Ultimate Wine Toolbox.",
            "Affiche sa sortie dans la fenêtre de terminal.",
        ],
        "command": "curl -fsSL https://bit.ly/ultimate-wine-toolbox | bash",
        "warning": "La sortie et les éventuelles questions de l’installateur s’affichent dans le terminal.",
    },
    {
        "name": "RGSX",
        "author": "By RetroGameSets",
        "tag": "PORTAIL · TÉLÉCHARGEMENTS",
        "description": [
            "Installe Retro Game Sets Xtra (RGSX).",
            "Le portail sera ajouté aux ports Batocera.",
        ],
        "command": "curl -L bit.ly/rgsx-install | sh",
        "warning": "La sortie et les éventuelles questions de l’installateur s’affichent dans le terminal.",
    },
]

WIDTH, HEIGHT = 1280, 720
BG = (8, 13, 25)
PANEL = (18, 27, 45)
PANEL_HI = (25, 42, 65)
EDGE = (38, 58, 83)
WHITE = (239, 244, 250)
MUTED = (151, 169, 190)
TEAL = (47, 225, 183)
BLUE = (78, 158, 255)
ORANGE = (255, 186, 87)
RED = (255, 110, 120)
BACK_BUTTON = pygame.Rect(684, 493, 150, 48)
LAUNCH_BUTTON = pygame.Rect(852, 493, 198, 48)
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
MENU_START_Y = 264
MENU_CARD_HEIGHT = 70
MENU_CARD_GAP = 9
MENU_VISIBLE = 4


def wrap(text, font, max_width):
    result, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and font.size(trial)[0] > max_width:
            result.append(line)
            line = word
        else:
            line = trial
    if line:
        result.append(line)
    return result


class Toolbox:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        pygame.mouse.set_visible(True)
        self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Batocera Ultimate Toolbox")
        self.surface = pygame.Surface((WIDTH, HEIGHT))
        self.scale = min(self.window.get_width() / WIDTH, self.window.get_height() / HEIGHT)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("dejavusans", 21)
        self.small = pygame.font.SysFont("dejavusans", 16)
        self.medium = pygame.font.SysFont("dejavusans", 25, bold=True)
        self.title = pygame.font.SysFont("dejavusans", 43, bold=True)
        self.hero = pygame.font.SysFont("dejavusans", 30, bold=True)
        self.terminal_font = pygame.font.SysFont("dejavusansmono", 16)
        self.avatar = None
        avatar_path = Path(__file__).resolve().with_name("avatar.png")
        try:
            source_avatar = pygame.image.load(str(avatar_path)).convert_alpha()
            aw, ah = source_avatar.get_size()
            factor = min(170 / aw, 98 / ah)
            size = (max(1, round(aw * factor)), max(1, round(ah * factor)))
            self.avatar = pygame.transform.smoothscale(source_avatar, size)
        except (pygame.error, OSError):
            pass
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            stick = pygame.joystick.Joystick(i)
            stick.init()
            self.joysticks.append(stick)
        self.selected = 0
        self.menu_offset = 0
        self.confirm_choice = 1
        self.page = "home"
        self.running = True
        self.notice = ""
        self.output_item = None
        self.output_lines = []
        self.output_code = None
        self.show_splash()
        self.check_for_updates()

    def text(self, value, x, y, color=WHITE, font=None):
        self.surface.blit((font or self.font).render(value, True, color), (x, y))

    def centered(self, value, x, y, color=WHITE, font=None):
        rendered = (font or self.font).render(value, True, color)
        self.surface.blit(rendered, (x - rendered.get_width() // 2, y))

    def rounded(self, rect, color, radius=18, border=None):
        pygame.draw.rect(self.surface, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(self.surface, border, rect, width=1, border_radius=radius)

    def present(self):
        self.window.fill((0, 0, 0))
        size = (int(WIDTH * self.scale), int(HEIGHT * self.scale))
        frame = pygame.transform.smoothscale(self.surface, size)
        self.window.blit(frame, ((self.window.get_width() - size[0]) // 2,
                                 (self.window.get_height() - size[1]) // 2))
        pygame.display.flip()

    def show_splash(self):
        logo_path = Path(__file__).resolve().with_name("Logo.jpg")
        if logo_path.is_file():
            logo = pygame.image.load(str(logo_path)).convert()
            self.surface.blit(pygame.transform.smoothscale(logo, (WIDTH, HEIGHT)), (0, 0))
        else:
            self.surface.fill(BG)

        # A restrained footer leaves the supplied logo as the focus.
        shade = pygame.Surface((WIDTH, 90), pygame.SRCALPHA)
        shade.fill((5, 10, 20, 175))
        self.surface.blit(shade, (0, HEIGHT - 90))
        self.text("BATOCERA ULTIMATE TOOLBOX", 48, HEIGHT - 70, WHITE, self.medium)
        self.text("Appuie sur une touche pour continuer", 48, HEIGHT - 39, MUTED, self.small)
        self.present()

        start = pygame.time.get_ticks()
        duration = 2400
        while self.running and pygame.time.get_ticks() - start < duration:
            elapsed = pygame.time.get_ticks() - start
            progress = min(1.0, elapsed / duration)
            pygame.draw.rect(self.surface, (12, 21, 35), (48, HEIGHT - 8, WIDTH - 96, 3))
            pygame.draw.rect(self.surface, TEAL,
                             (48, HEIGHT - 8, int((WIDTH - 96) * progress), 3))
            self.present()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN,
                                     pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION):
                    return
            self.clock.tick(30)

    def show_update_status(self, message):
        self.surface.fill(BG)
        pygame.draw.circle(self.surface, (12, 36, 50), (WIDTH // 2, 190), 205)
        self.centered("BATOCERA ULTIMATE TOOLBOX", WIDTH // 2, 310, WHITE, self.title)
        self.centered(message, WIDTH // 2, 390, TEAL, self.font)
        self.present()

    @staticmethod
    def version_key(value):
        value = value.strip()
        if not re.fullmatch(r"\d+(?:\.\d+){1,3}", value):
            return None
        parts = [int(part) for part in value.split(".")]
        return tuple((parts + [0, 0, 0, 0])[:4])

    def check_for_updates(self):
        app_dir = Path(__file__).resolve().parent
        version_path = app_dir / "version"
        repository_path = app_dir / "repository"
        if not version_path.is_file() or not repository_path.is_file():
            return

        try:
            repository = repository_path.read_text(encoding="utf-8").strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
                return
            local_version = version_path.read_text(encoding="utf-8").strip()
            local_key = self.version_key(local_version)
            if local_key is None:
                return

            self.show_update_status(f"Vérification de la version {local_version}…")
            request = urllib.request.Request(
                f"https://raw.githubusercontent.com/{repository}/main/toolbox/version",
                headers={"User-Agent": "DreamerCG-Toolbox"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                remote_version = response.read(64).decode("utf-8", "replace").strip()
            remote_key = self.version_key(remote_version)
            if remote_key is None or remote_key <= local_key:
                return

            self.install_update_files(repository, remote_version)
            self.show_update_status(f"Toolbox mise à jour en version {remote_version}.")
            pygame.time.wait(900)
            pygame.quit()
            os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])
        except Exception as exc:
            print(f"Mise à jour DreamerCG Toolbox ignorée : {exc}", file=sys.stderr)

    def install_update_files(self, repository, expected_version):
        app_dir = Path(__file__).resolve().parent
        self.show_update_status(f"Téléchargement de la mise à jour {expected_version}…")
        allowed = {"toolbox_ui.py", "Logo.jpg", "avatar.png", "version", "repository"}
        with tempfile.TemporaryDirectory(prefix=".toolbox-update-", dir=str(app_dir)) as temp_dir:
            stage = Path(temp_dir)
            staged = {}
            for name in allowed:
                url = f"https://raw.githubusercontent.com/{repository}/main/toolbox/{name}"
                request = urllib.request.Request(url, headers={"User-Agent": "DreamerCG-Toolbox"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    contents = response.read(8 * 1024 * 1024 + 1)
                if len(contents) > 8 * 1024 * 1024:
                    raise RuntimeError(f"Fichier de mise à jour trop volumineux : {name}")
                target = stage / name
                target.write_bytes(contents)
                staged[name] = target

            if staged.keys() != allowed:
                missing = ", ".join(sorted(allowed - staged.keys()))
                raise RuntimeError(f"Fichiers manquants dans la mise à jour : {missing}")
            if staged["version"].read_text(encoding="utf-8").strip() != expected_version:
                raise RuntimeError("La version de l’archive ne correspond pas à la version annoncée.")
            if staged["repository"].read_text(encoding="utf-8").strip() != repository:
                raise RuntimeError("Le dépôt indiqué dans l’archive ne correspond pas.")

            previous = {
                name: (app_dir / name).read_bytes() if (app_dir / name).is_file() else None
                for name in allowed
            }
            order = ["toolbox_ui.py", "Logo.jpg", "avatar.png", "repository", "version"]
            try:
                for name in order:
                    os.replace(staged[name], app_dir / name)
            except Exception:
                for name, content in previous.items():
                    destination = app_dir / name
                    if content is None:
                        destination.unlink(missing_ok=True)
                    else:
                        restore = stage / (name + ".restore")
                        restore.write_bytes(content)
                        os.replace(restore, destination)
                raise

    def mouse_position(self):
        """Translate window coordinates to the 1280x720 menu canvas."""
        mx, my = pygame.mouse.get_pos()
        left = (self.window.get_width() - WIDTH * self.scale) / 2
        top = (self.window.get_height() - HEIGHT * self.scale) / 2
        return ((mx - left) / self.scale, (my - top) / self.scale)

    @staticmethod
    def card_at(pos, offset=0):
        x, y = pos
        if 64 <= x <= 806:
            slot_height = MENU_CARD_HEIGHT + MENU_CARD_GAP
            row = int((y - MENU_START_Y) // slot_height)
            if 0 <= row < MENU_VISIBLE:
                card_y = MENU_START_Y + row * slot_height
                index = offset + row
                if card_y <= y <= card_y + MENU_CARD_HEIGHT and index < len(INSTALLERS):
                    return index
        return None

    def chrome(self, section="INSTALLATEURS"):
        self.surface.fill(BG)
        # Subtle arcade-style background glow and grid.
        pygame.draw.circle(self.surface, (12, 36, 50), (1085, 75), 250)
        for x in range(0, WIDTH, 48):
            pygame.draw.line(self.surface, (13, 22, 36), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 48):
            pygame.draw.line(self.surface, (13, 22, 36), (0, y), (WIDTH, y), 1)
        if self.avatar:
            self.surface.blit(self.avatar, (48, (105 - self.avatar.get_height()) // 2))
        self.text("BATOCERA ULTIMATE", 244, 36, WHITE, self.medium)
        self.text("TOOLBOX", 245, 64, TEAL, self.small)
        self.text(section, WIDTH - 232, 54, TEAL, self.small)
        pygame.draw.line(self.surface, EDGE, (48, 105), (WIDTH - 48, 105), 1)

    def draw_home(self):
        if self.selected < self.menu_offset:
            self.menu_offset = self.selected
        elif self.selected >= self.menu_offset + MENU_VISIBLE:
            self.menu_offset = self.selected - MENU_VISIBLE + 1
        self.menu_offset = max(0, min(self.menu_offset, max(0, len(INSTALLERS) - MENU_VISIBLE)))
        self.chrome()
        self.text("OUTILS COMMUNAUTAIRES — BATOCERA FAN FR", 76, 126, TEAL, self.small)
        self.text("Tes outils gaming réunis au même endroit.", 74, 164, WHITE, self.hero)
        self.text("CHOISIS TON OUTIL", 78, 231, MUTED, self.small)

        visible_items = INSTALLERS[self.menu_offset:self.menu_offset + MENU_VISIBLE]
        for row, item in enumerate(visible_items):
            index = self.menu_offset + row
            y = MENU_START_Y + row * (MENU_CARD_HEIGHT + MENU_CARD_GAP)
            active = index == self.selected
            color = PANEL_HI if active else PANEL
            border = TEAL if active else EDGE
            self.rounded((64, y, 742, MENU_CARD_HEIGHT), color, 15, border)
            pygame.draw.rect(self.surface, TEAL if index == 0 else BLUE,
                             (64, y + 12, 5, 46), border_radius=3)
            self.text(item["name"], 92, y + 7, WHITE, self.medium)
            self.text(item["tag"], 94, y + 39, TEAL if index == 0 else BLUE, self.small)
            if active:
                self.rounded((727, y + 23, 68, 25), (19, 59, 63), 10, TEAL)
                label = self.small.render("Valider", True, TEAL)
                self.surface.blit(label, label.get_rect(center=(761, y + 35)))

        item = INSTALLERS[self.selected]
        self.rounded((835, 144, 380, 432), PANEL, 20, EDGE)
        self.text("À PROPOS", 863, 173, MUTED, self.small)
        self.text(item["name"], 862, 207, WHITE, self.medium)
        self.text(item["author"], 862, 241, TEAL, self.small)
        pygame.draw.line(self.surface, EDGE, (862, 267), (1185, 267), 1)
        description_y = 291
        for paragraph in item["description"]:
            for line in wrap(paragraph, self.small, 318):
                self.text(line, 862, description_y, MUTED, self.small)
                description_y += 20
        self.rounded((862, 407, 318, 105), (32, 32, 35), 13, (105, 81, 47))
        self.text("ACTION DE L’INSTALLATEUR", 878, 423, ORANGE, self.small)
        for i, line in enumerate(wrap(item["warning"], self.small, 280)[:3]):
            self.text(line, 878, 449 + i * 20, (221, 211, 192), self.small)
        self.footer("↑ ↓  Naviguer", "A / Entrée  Ouvrir", "B / Échap  Quitter")

    def footer(self, left, middle, right):
        pygame.draw.line(self.surface, EDGE, (48, 624), (WIDTH - 48, 624), 1)
        self.text(left, 66, 650, MUTED, self.small)
        self.centered(middle, WIDTH // 2, 650, WHITE, self.small)
        rendered = self.small.render(right, True, MUTED)
        self.surface.blit(rendered, (WIDTH - 65 - rendered.get_width(), 650))

    def draw_confirm(self):
        self.chrome("CONFIRMATION")
        item = INSTALLERS[self.selected]
        self.rounded((180, 150, 920, 420), PANEL, 22, EDGE)
        self.rounded((218, 186, 52, 52), (66, 49, 26), 15, (117, 84, 41))
        self.centered("!", 244, 192, ORANGE, self.title)
        self.text("Confirmer le lancement ?", 293, 190, WHITE, self.title)
        self.text("INSTALLATEUR SÉLECTIONNÉ", 234, 277, MUTED, self.small)
        self.text(item["name"], 234, 305, TEAL, self.medium)
        self.text("Commande exécutée dans le terminal :", 234, 354, WHITE, self.font)
        self.text(item["command"], 234, 396, ORANGE, self.small)
        back_active = self.confirm_choice == 0
        self.rounded(BACK_BUTTON,
                     PANEL_HI if back_active else PANEL, 12,
                     TEAL if back_active else EDGE)
        self.centered("Retour", BACK_BUTTON.centerx, 505,
                      WHITE if back_active else MUTED, self.small)
        launch_active = self.confirm_choice == 1
        self.rounded(LAUNCH_BUTTON,
                     (22, 77, 69) if launch_active else PANEL, 12,
                     TEAL if launch_active else EDGE)
        self.centered("Lancer", LAUNCH_BUTTON.centerx, 505,
                      WHITE if launch_active else MUTED, self.medium)
        self.footer("← → / stick  Choisir", "A / Entrée  Valider", "B / Échap  Retour")

    def draw_notice(self):
        self.chrome("INFORMATION")
        self.rounded((180, 150, 920, 420), PANEL, 22, EDGE)
        self.text("Installation non lancée", 230, 197, WHITE, self.title)
        for i, line in enumerate(wrap(self.notice, self.font, 810)):
            self.text(line, 232, 285 + i * 34, ORANGE, self.font)
        self.footer("A / Entrée  Fermer", "", "B / Échap  Fermer")

    def draw_installer_output(self, item, lines, running, return_code=None):
        self.chrome("INSTALLATION EN COURS" if running else "RÉSULTAT DE L’INSTALLATION")
        self.rounded((80, 130, 1120, 470), PANEL, 22, EDGE)
        self.text(item["name"], 120, 158, WHITE, self.title)
        if running:
            self.text("Commande en cours…", 122, 220, TEAL, self.font)
        elif return_code == 0:
            self.text("La commande s’est terminée sans erreur.", 122, 220, TEAL, self.font)
        else:
            self.text(f"La commande a échoué (code {return_code}).", 122, 220, RED, self.font)

        self.rounded((115, 260, 1050, 330), (7, 12, 21), 12, EDGE)
        visible = []
        for line in lines:
            visible.extend(wrap(line, self.terminal_font, 1000) or [""])
        for index, line in enumerate(visible[-16:]):
            self.text(line, 135, 275 + index * 19, MUTED, self.terminal_font)
        if running:
            self.footer("Installation en cours", "", "")
        else:
            self.footer("A / Entrée  Retour au menu", "", "B / Échap  Retour")

    def confirm_install(self):
        item = INSTALLERS[self.selected]
        self.confirm_choice = 1
        self.page = "confirm"
        while self.running:
            self.draw_confirm()
            self.present()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                if event.type == pygame.MOUSEMOTION:
                    x, y = self.mouse_position()
                    if BACK_BUTTON.collidepoint(x, y):
                        self.confirm_choice = 0
                    elif LAUNCH_BUTTON.collidepoint(x, y):
                        self.confirm_choice = 1
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = self.mouse_position()
                    if LAUNCH_BUTTON.collidepoint(x, y):
                        self.confirm_choice = 1
                    if BACK_BUTTON.collidepoint(x, y):
                        self.confirm_choice = 0
                    if BACK_BUTTON.collidepoint(x, y) or LAUNCH_BUTTON.collidepoint(x, y):
                        if self.confirm_choice == 1:
                            self.run_installer(item)
                            return
                        else:
                            self.page = "home"
                        return
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_b):
                        self.page = "home"
                        return
                    if event.key in (pygame.K_LEFT, pygame.K_UP):
                        self.confirm_choice = 0
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                        self.confirm_choice = 1
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.confirm_choice == 1:
                            self.run_installer(item)
                            return
                        else:
                            self.page = "home"
                        return
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button in (0, 2):
                        if self.confirm_choice == 1:
                            self.run_installer(item)
                            return
                        else:
                            self.page = "home"
                        return
                    if event.button in (1, 3, 7):
                        self.page = "home"
                        return
                if event.type == pygame.JOYHATMOTION:
                    x, y = event.value
                    if x < 0 or y > 0:
                        self.confirm_choice = 0
                    elif x > 0 or y < 0:
                        self.confirm_choice = 1
                if event.type == pygame.JOYAXISMOTION:
                    if event.axis == 0:
                        if event.value < -.65:
                            self.confirm_choice = 0
                            pygame.time.wait(140)
                        elif event.value > .65:
                            self.confirm_choice = 1
                            pygame.time.wait(140)
                    elif event.axis == 1:
                        if event.value < -.65:
                            self.confirm_choice = 0
                            pygame.time.wait(140)
                        elif event.value > .65:
                            self.confirm_choice = 1
                            pygame.time.wait(140)
            self.clock.tick(30)

    def run_installer(self, item):
        if not Path("/userdata/roms/ports").is_dir():
            self.notice = (
                "Cette commande est prévue pour Batocera. L’aperçu sur ce PC ne peut pas "
                "installer Linux Loader ou la Toolbox Switch. Lance la toolbox depuis Batocera."
            )
            self.page = "notice"
            return
        output = queue.Queue()
        lines = []
        try:
            process = subprocess.Popen(
                ["bash", "-o", "pipefail", "-lc", item["command"]],
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            self.output_item = item
            self.output_lines = [f"Impossible de démarrer bash : {exc}"]
            self.output_code = 127
            self.page = "result"
            return

        def read_output():
            for line in process.stdout:
                output.put(line.rstrip("\r\n"))
            process.stdout.close()

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        self.page = "running"
        while process.poll() is None or reader.is_alive() or not output.empty():
            while True:
                try:
                    line = output.get_nowait()
                except queue.Empty:
                    break
                line = ANSI_ESCAPE.sub("", line)
                lines.append(line)
                lines = lines[-300:]
                print(line, flush=True)
            self.draw_installer_output(item, lines, True)
            self.present()
            pygame.event.pump()
            self.clock.tick(30)

        return_code = process.wait()
        while not output.empty():
            line = ANSI_ESCAPE.sub("", output.get_nowait())
            lines.append(line)
            print(line, flush=True)
        self.output_item = item
        self.output_lines = lines
        self.output_code = return_code
        self.page = "result"
        self.draw_installer_output(item, lines, False, return_code)
        self.present()

    def loop(self):
        while self.running:
            if self.page == "notice":
                self.draw_notice()
            elif self.page in ("running", "result") and self.output_item:
                self.draw_installer_output(
                    self.output_item, self.output_lines,
                    self.page == "running", self.output_code,
                )
            else:
                self.draw_home()
            self.present()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.page == "notice" and (
                    event.type == pygame.KEYDOWN and event.key in
                    (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_b)
                    or event.type == pygame.MOUSEBUTTONDOWN
                    or event.type == pygame.JOYBUTTONDOWN
                ):
                    self.page = "home"
                elif self.page == "result" and (
                    event.type == pygame.KEYDOWN and event.key in
                    (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_b)
                    or event.type == pygame.MOUSEBUTTONDOWN
                    or event.type == pygame.JOYBUTTONDOWN
                ):
                    self.page = "home"
                elif event.type == pygame.MOUSEMOTION:
                    hovered = self.card_at(self.mouse_position(), self.menu_offset)
                    if hovered is not None:
                        self.selected = hovered
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        clicked = self.card_at(self.mouse_position(), self.menu_offset)
                        if clicked is not None:
                            self.selected = clicked
                            self.confirm_install()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected = min(self.selected + 1, len(INSTALLERS) - 1)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.selected = max(self.selected - 1, 0)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.confirm_install()
                elif event.type == pygame.JOYHATMOTION:
                    _, y = event.value
                    if y == -1:
                        self.selected = min(self.selected + 1, len(INSTALLERS) - 1)
                    elif y == 1:
                        self.selected = max(self.selected - 1, 0)
                elif event.type == pygame.JOYAXISMOTION and event.axis == 1:
                    if event.value > .65:
                        self.selected = min(self.selected + 1, len(INSTALLERS) - 1)
                        pygame.time.wait(140)
                    elif event.value < -.65:
                        self.selected = max(self.selected - 1, 0)
                        pygame.time.wait(140)
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button in (0, 2):
                        self.confirm_install()
                    elif event.button in (1, 3, 7):
                        self.running = False
            self.clock.tick(30)
        pygame.quit()
if __name__ == "__main__":
    Toolbox().loop()
