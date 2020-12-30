import configparser
import math

from pynput.keyboard import Key, KeyCode, Listener, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
from util.agent import VirxERLU, Vector
from util import tools
from util import utils


class Cyborg(VirxERLU):
    def __init__(self):
        super().__init__("Cyborg")

    def symbolToKey(self, symbol):
        key = self.config.get("Key Map", symbol).lower()

        if key in Button._member_names_:
            return Button[key]

        if key in Key._member_names_:
            return Key[key]

        return key

    def on_key_press(self, key):
        if key == self.cancel_key:
            print(self.name + " requested all operations be canceled")
            self.mode = 0

        if key == self.target_key:
            print(self.name + " requested shots to be taken on the opponent's net")
            self.mode = 1

        if key == self.antitarget_key:
            print(self.name + " requested shots that aren't own goals to be taken")
            self.mode = 2

    def init(self):
        foe_team = -1 if self.team == 1 else 1
        team = -foe_team

        self.best_shot = (Vector(foe_team * 793, foe_team * 5213, 321.3875), Vector(-foe_team * 793, foe_team * 5213, 321.3875))
        self.anti_shot = (Vector(-team * 2048, team * 5120, 2000), Vector(team * 2048, team * 5120, 2000))

        self.last_controller = [0, 0, 0, 0, 0]
        self.last_car_air = False
        self.mode = 0

        self.keyboard = KeyboardController()
        self.mouse = MouseController()

        self.config = configparser.ConfigParser()
        self.config.read('G:/Cyborg/cyborg.cfg')

        self.keymap = [
            [None, self.symbolToKey("w"), self.symbolToKey("s")],
            [None, self.symbolToKey("d"), self.symbolToKey("a")],
            [self.symbolToKey("handbrake"), self.symbolToKey("e"), self.symbolToKey("q")],
            self.symbolToKey("boost"),
            self.symbolToKey("jump")
        ]

        self.shot_types = [
            self.config.get("Shots", "aerial").lower() == 'true',
            self.config.get("Shots", "double_jump").lower() == 'true',
            self.config.get("Shots", "jump").lower() == 'true',
            self.config.get("Shots", "ground").lower() == 'true'
        ]

        shots = []
        if self.shot_types[0]: shots.append("aerial shots")
        if self.shot_types[1]: shots.append("double jump shots")
        if self.shot_types[2]: shots.append("jump shots")
        if self.shot_types[3]: shots.append("ground shots")
        
        if len(shots) > 0:
            if len(shots) > 1:
                shots[-1] = "and " + shots[-1]
                print(self.name + " requests the following shot types to be considered: " + ", ".join(shots))
            else:
                print(self.name + " requests only the following shot type be considered: " + shots[0])
        else:
            print(self.name + " requests no shots to ever be considered, no matter what")

        target_key = self.config.get("Key Map", "target").lower()
        self.target_key = key[target_key] if target_key in Key._member_names_ else KeyCode(char=target_key)

        antitarget_key = self.config.get("Key Map", "antitarget").lower()
        self.antitarget_key = key[antitarget_key] if antitarget_key in Key._member_names_ else KeyCode(char=antitarget_key)

        cancel_key = self.config.get("Key Map", "cancel").lower()
        self.cancel_key = key[cancel_key] if cancel_key in Key._member_names_ else KeyCode(char=cancel_key)

        target_listener = Listener(on_press=self.on_key_press)
        target_listener.start()

    def run(self):
        if self.mode == 0:
            if not self.is_clear():
                self.clear()
            return

        if not self.shooting or self.odd_tick == 0:
            shot = tools.find_shot(self, self.best_shot if self.mode == 1 else self.anti_shot, 6, *self.shot_types)

            if shot is not None:
                if self.shooting:
                    current_shot_name = self.stack[0].__class__.__name__
                    new_shot_name = shot.__class__.__name__

                    if new_shot_name is current_shot_name:
                        self.stack[0].update(shot)
                        return
            
                self.clear()
                self.shooting = True
                self.push(shot)
                return

    def handle_controller(self):
        # this converts the controller that would've been sent to RLBot into keyboard/mouse presses instead

        controller = [self.controller.pitch * -1, self.controller.yaw, self.controller.roll] if self.me.airborne else [self.controller.throttle, self.controller.steer, self.controller.handbrake]
        controller += [self.controller.boost, self.controller.jump]

        if self.me.airborne != self.last_car_air:
            if self.last_controller[2] != 0:
                self.keyboard.release(self.keymap[2][self.last_controller[2 if self.last_car_air else 0]])

        # throttle/pitch/steer/yaw/roll
        for i in range(3 if self.me.airborne else 2):
            controller[i] = 0 if abs(controller[i]) <= 0.01 else utils.sign(controller[i])

            if self.last_controller[i] != controller[i]:
                if self.last_controller[i] != 0:
                    self.keyboard.release(self.keymap[i][self.last_controller[i]])

                if controller[i] != 0:
                    self.keyboard.press(self.keymap[i][controller[i]])

        # handbrake
        if not self.me.airborne:
            controller[2] = 1 if controller[2] else 0

            if self.last_controller[2] != controller[2]:
                if self.last_controller[2] != 0:
                    self.keyboard.release(self.keymap[2][0])

                if controller[2] == 1:
                    self.keyboard.press(self.keymap[2][0])

        # boost/jump
        for i in (3, 4):
            controller[i] = 1 if controller[i] else 0

            if self.last_controller[i] != controller[i]:
                if self.last_controller[i]:
                    self.mouse.release(self.keymap[i])

                if controller[i]:
                    self.mouse.press(self.keymap[i])

        self.last_controller = controller
        self.last_car_air = self.me.airborne


if __name__ == "__main__":
    cyborg = Cyborg()
    cyborg.main()
