LOOK_R = '( ⚆_⚆)'
LOOK_L = '(☉_☉ )'
LOOK_R_HAPPY = '( ◕‿◕)'
LOOK_L_HAPPY = '(◕‿◕ )'
SLEEP = '(⇀‿‿↼)'
SLEEP2 = '(≖‿‿≖)'
AWAKE = '(◕‿‿◕)'
BORED = '(-__-)'
INTENSE = '(°▃▃°)'
COOL = '(⌐■_■)'
HAPPY = '(•‿‿•)'
GRATEFUL = '(^‿‿^)'
EXCITED = '(ᵔ◡◡ᵔ)'
MOTIVATED = '(☼‿‿☼)'
DEMOTIVATED = '(≖__≖)'
SMART = '(✜‿‿✜)'
LONELY = '(ب__ب)'
SAD = '(╥☁╥ )'
ANGRY = "(-_-')"
FRIEND = '(♥‿‿♥)'
BROKEN = '(☓‿‿☓)'
DEBUG = '(#__#)'
UPLOAD = '(1__0)'
UPLOAD1 = '(1__1)'
UPLOAD2 = '(0__1)'


def load_from_config(config):
    for face_name, face_value in config.items():
        globals()[face_name.upper()] = face_value


class Faces:
    def __init__(self, faces, position, state):
        self._faces = faces
        self._position = position
        self._state = state

    def draw(self, canvas, width, height):
        face = self._state.get('face')
        if face in self._faces:
            canvas.text(self._position, self._faces[face], font=None, fill=0)


def load_faces(config):
    load_from_config(config['ui']['faces'])
    
    faces = {
        'LOOK_R': LOOK_R,
        'LOOK_L': LOOK_L,
        'LOOK_R_HAPPY': LOOK_R_HAPPY,
        'LOOK_L_HAPPY': LOOK_L_HAPPY,
        'SLEEP': SLEEP,
        'SLEEP2': SLEEP2,
        'AWAKE': AWAKE,
        'BORED': BORED,
        'INTENSE': INTENSE,
        'COOL': COOL,
        'HAPPY': HAPPY,
        'GRATEFUL': GRATEFUL,
        'EXCITED': EXCITED,
        'MOTIVATED': MOTIVATED,
        'DEMOTIVATED': DEMOTIVATED,
        'SMART': SMART,
        'LONELY': LONELY,
        'SAD': SAD,
        'ANGRY': ANGRY,
        'FRIEND': FRIEND,
        'BROKEN': BROKEN,
        'DEBUG': DEBUG,
        'UPLOAD': UPLOAD,
        'UPLOAD1': UPLOAD1,
        'UPLOAD2': UPLOAD2
    }
    
    return faces
