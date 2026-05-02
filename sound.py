import pygame as pg


class Sound:
    """
    Loads and stores all the game's audio — sound effects and background music.

    Every sound is loaded once here at the start of the game and saved as an
    attribute. Other parts of the game just call .play() on the one they need:
        self.game.sound.shotgun.play()
        self.game.sound.npc_pain.play()

    pygame's mixer lets multiple sounds play at the same time automatically,
    so the shotgun sound and an enemy death sound can overlap without any
    extra work on our end.

    The background music is handled separately through pg.mixer.music because
    it's a long audio file that streams from disk as it plays, rather than
    being loaded fully into memory like the short sound effects.
    """

    def __init__(self, game):
        self.game = game
        pg.mixer.init()  # Start up the audio system

        self.path = 'resources/sound/'  # Folder where all audio files live

        # ── Sound effects ─────────────────────────────────────────────────────
        # These are short clips loaded fully into memory for instant playback.
        self.shotgun     = pg.mixer.Sound(self.path + 'shotgun.wav')      # Player fires the gun
        self.npc_pain    = pg.mixer.Sound(self.path + 'npc_pain.wav')     # Enemy gets hit
        self.npc_death   = pg.mixer.Sound(self.path + 'npc_death.wav')    # Enemy dies
        self.npc_shot    = pg.mixer.Sound(self.path + 'npc_attack.wav')   # Enemy fires at the player
        self.npc_shot.set_volume(0.2)  # Turn this down so it doesn't drown out everything else
        self.player_pain = pg.mixer.Sound(self.path + 'player_pain.wav')  # Player takes damage

        # ── Background music ──────────────────────────────────────────────────
        # Loaded as a stream rather than into memory — better for long audio files.
        # The actual playback is started in Game.new_game() with pg.mixer.music.play(-1).
        self.theme = pg.mixer.music.load(self.path + 'theme.mp3')
        pg.mixer.music.set_volume(0.3)  # Keep the music at 30% so it sits behind the action