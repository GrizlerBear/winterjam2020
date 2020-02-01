import pygame
import sys
import os
import math

# Handle cli flags
windowed = "--windowed" in sys.argv
show_fps = "--showfps" in sys.argv
if "--debug" in sys.argv:
    windowed = True
    show_fps = True


# Resolution variables, Display is streched to match Screen which can be set by user
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

if os.path.isfile("data/settings.txt"):
    print("Settings file found!")
    video_settings = open("data/settings.txt").read().splitlines()
    for line in video_settings:
        if line.startswith("resolution="):
            SCREEN_WIDTH = int(line[line.index("=") + 1:line.index("x")])
            SCREEN_HEIGHT = int(line[line.index("x") + 1:])
            aspect_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
            if aspect_ratio == 4 / 3:
                DISPLAY_HEIGHT = 960
            elif aspect_ratio == 16 / 10:
                DISPLAY_HEIGHT = 840
            elif aspect_ratio == 16 / 9:
                DISPLAY_HEIGHT = 720
else:
    print("No settings file found!")
print("Resolution set to " + str(SCREEN_WIDTH) + "x" + str(SCREEN_HEIGHT) + ".")

SCALE = SCREEN_WIDTH / DISPLAY_WIDTH

# Timing variables
TARGET_FPS = 60
SECOND = 1000
UPDATE_TIME = SECOND / 60.0
fps = 0
frames = 0
dt = 0
before_time = 0
before_sec = 0

# Init pygame
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
global screen
if windowed:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), 0, 32)
else:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
display = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT))
clock = pygame.time.Clock()


# Input variables
input_queue = []
input_states = {"player up": False, "player right": False, "player down": False, "player left": False}
mouse_x = 0
mouse_y = 0


# Color variables
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)
YELLOW = (255, 255, 0)


# Images
image_path = "res/"
image_cache = {}


def get_image(path, has_alpha, alpha=255, subrect=None):
    global image_cache

    if path not in image_cache.keys():
        if has_alpha:
            image_cache[path] = pygame.image.load(image_path + path + ".png").convert_alpha()
        else:
            image_cache[path] = pygame.image.load(image_path + path + ".png").convert()

    return_path = path
    if alpha != 255:
        return_path = path + "&alpha=" + str(alpha)
        if return_path not in image_cache.keys():
            new_image = image_cache[path].copy()
            new_image.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
            image_cache[return_path] = new_image

    if subrect is not None:
        return image_cache[return_path].subsurface(pygame.Rect(subrect))
    else:
        return image_cache[return_path]


def rotate_image(image, angle, origin_pos=None):
    if origin_pos is None:
        origin_pos = image.get_rect().center

    # calculate the axis aligned bounding box of the rotated image
    w, h = image.get_size()
    box = [pygame.math.Vector2(p) for p in [(0, 0), (w, 0), (w, -h), (0, -h)]]
    box_rotate = [p.rotate(angle) for p in box]
    min_box = (min(box_rotate, key=lambda p: p[0])[0], min(box_rotate, key=lambda p: p[1])[1])
    max_box = (max(box_rotate, key=lambda p: p[0])[0], max(box_rotate, key=lambda p: p[1])[1])

    # calculate the translation of the pivot
    pivot = pygame.math.Vector2(origin_pos[0], -origin_pos[1])
    pivot_rotate = pivot.rotate(angle)
    pivot_move = pivot_rotate - pivot

    rotated_image = pygame.transform.rotate(image, angle)
    offset = (int(min_box[0] - origin_pos[0] - pivot_move[0]), int(pivot_move[1] - max_box[1] - origin_pos[1]))

    return rotated_image, offset


# Fonts
font_small = pygame.font.SysFont("Serif", 11)


# game states
EXIT = -1
MAIN_LOOP = 0


def get_distance(point1, point2):
    return math.sqrt(((point2[0] - point1[0]) ** 2) + ((point2[1] - point1[1]) ** 2))


def sum_vectors(a, b):
    return (a[0] + b[0], a[1] + b[1])


def scale_vector(old_vector, new_magnitude):
    old_magnitude = math.sqrt((old_vector[0] ** 2) + (old_vector[1] ** 2))
    if old_magnitude == 0:
        return (0, 0)
    scale = new_magnitude / old_magnitude
    new_x = old_vector[0] * scale
    new_y = old_vector[1] * scale
    return (new_x, new_y)


def get_center(rect):
    return ((rect[0] + (rect[2] // 2)), (rect[1] + (rect[3] // 2)))


def rects_collide(rect1, rect2):
    r1_center_x, r1_center_y = get_center(rect1)
    r2_center_x, r2_center_y = get_center(rect2)
    return abs(r1_center_x - r2_center_x) * 2 < rect1[2] + rect2[2] and abs(r1_center_y - r2_center_y) * 2 < rect1[3] + rect2[3]


def point_in_rect(point, rect):
    return rects_collide((point[0], point[1], 1, 1), rect)


def get_point_angle(point1, point2):
    xdiff = point2[0] - point1[0]
    ydiff = point2[1] - point1[1]
    angle = math.degrees(math.atan2(ydiff, xdiff))
    if angle > 0:
        angle = 360 - angle
    elif angle < 0:
        angle *= -1

    return angle


class Entity():
    def __init__(self, image, has_alpha):
        image_object = get_image(image, has_alpha)

        self.image = image
        self.image_append = ""
        self.has_alpha = has_alpha
        self.rotation = None
        self.offset_x = 0
        self.offset_y = 0
        self.x = 0
        self.y = 0
        self.width = image_object.get_rect().width
        self.height = image_object.get_rect().height
        self.vx = 0
        self.vy = 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def get_x(self):
        return int(round(self.x)) + self.offset_x

    def get_y(self):
        return int(round(self.y)) + self.offset_y

    def update_rect(self):
        image_obj = get_image(self.image, self.has_alpha)
        self.width, self.height = image_obj.get_rect().width, image_obj.get_rect().height

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def get_center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    def collides(self, other):
        return rects_collide(self.get_rect(), other)

    def check_collision(self, dt, collider):
        """
        This checks for a collision with a wall-like object and handles it if necessary
        """
        collides = False

        if self.collides(collider):
            collides = True

            x_step = self.vx * dt
            y_step = self.vy * dt

            # Since there was a collision, rollback our previous movement
            self.x -= x_step
            self.y -= y_step

            # Check to see if that collision happened due to x movement
            self.x += x_step
            x_caused_collision = self.collides(collider)
            self.x -= x_step

            # Check to see if that collision happened due to y movement
            self.y += y_step
            y_caused_collision = self.collides(collider)
            self.y -= y_step

            # If x/y didn't cause collision, we can move in x/y direction
            if not x_caused_collision:
                self.x += x_step
            if not y_caused_collision:
                self.y += y_step

        # This is for if we want to override the function and add extra behavior to the collision
        return collides

    def get_image(self, alpha=255):
        image = None
        if alpha == 255:
            image = get_image(self.image + self.image_append, self.has_alpha)
        else:
            image = get_image(self.image + self.image_append, self.has_alpha, alpha)
        if self.rotation is None:
            return image
        else:
            image, offset = rotate_image(image, self.rotation)
            self.offset_x, self.offset_y = offset
            return image


def game():
    running = True

    player = Entity("mouse", True)
    player.x, player.y = (492, 1818)
    player_dx, player_dy = (0, 0)
    player_speed = 3

    camera_x, camera_y = (0, 0)
    camera_offset_x, camera_offset_y = (player.width // 2) - (DISPLAY_WIDTH // 2), (player.height // 2) - (DISPLAY_HEIGHT // 2)

    while running:
        # Handle input
        handle_input()
        while len(input_queue) != 0:
            event = input_queue.pop()
            if event == ("player up", True):
                player_dy = -1
            elif event == ("player right", True):
                player_dx = 1
            elif event == ("player down", True):
                player_dy = 1
            elif event == ("player left", True):
                player_dx = -1
            elif event == ("player up", False):
                if input_states["player down"]:
                    player_dy = 1
                else:
                    player_dy = 0
            elif event == ("player right", False):
                if input_states["player left"]:
                    player_dx = -1
                else:
                    player_dx = 0
            elif event == ("player down", False):
                if input_states["player up"]:
                    player_dy = -1
                else:
                    player_dy = 0
            elif event == ("player left", False):
                if input_states["player right"]:
                    player_dx = 1
                else:
                    player_dx = 0

        # Update
        player.vx, player.vy = scale_vector((player_dx, player_dy), player_speed)
        player.update(dt)

        camera_x, camera_y = player.get_x() + camera_offset_x, player.get_y() + camera_offset_y

        # Render
        clear_display()

        display.blit(get_image("b_background", True), (0 - camera_x, 0 - camera_y))
        display.blit(player.get_image(), (player.get_x() - camera_x, player.get_y() - camera_y))

        if show_fps:
            render_fps()
        flip_display()
        tick()


def handle_input():
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                input_queue.append(("player up", True))
                input_states["player up"] = True
            elif event.key == pygame.K_d:
                input_queue.append(("player right", True))
                input_states["player right"] = True
            elif event.key == pygame.K_s:
                input_queue.append(("player down", True))
                input_states["player down"] = True
            elif event.key == pygame.K_a:
                input_queue.append(("player left", True))
                input_states["player left"] = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_w:
                input_queue.append(("player up", False))
                input_states["player up"] = False
            elif event.key == pygame.K_d:
                input_queue.append(("player right", False))
                input_states["player right"] = False
            elif event.key == pygame.K_s:
                input_queue.append(("player down", False))
                input_states["player down"] = False
            elif event.key == pygame.K_a:
                input_queue.append(("player left", False))
                input_states["player left"] = False
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            mouse_x = int(mouse_pos[0] / SCALE)
            mouse_y = int(mouse_pos[1] / SCALE)


    """
    elif event.type == pygame.KEYDOWN:
    if event.key == pygame.K_w etc etc
    elif event.type == pygame.KEYUP:
    elif event.type == pygame.MOUSEMOTION:
    mouse_pos = pygame.mouse.get_pos()
    mouse_x = int(mouse_pos[0] / SCALE)
    mouse_y = int(mouse_pos[1] / SCALE)
    """


def clear_display():
    pygame.draw.rect(display, BLACK, (0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT), False)


def flip_display():
    global frames

    pygame.transform.scale(display, (SCREEN_WIDTH, SCREEN_HEIGHT), screen)
    pygame.display.flip()
    frames += 1


def render_fps():
    text = font_small.render("FPS: " + str(fps), False, BLACK)
    display.blit(text, (0, 0))


def tick():
    global before_time, before_sec, fps, frames, dt

    # Update delta based on the time elapsed
    after_time = pygame.time.get_ticks()
    dt = (after_time - before_time) / UPDATE_TIME

    # Update fps if a second has passed
    if after_time - before_sec >= SECOND:
        fps = frames
        frames = 0
        before_sec += SECOND
    before_time = pygame.time.get_ticks()

    # Update pygame clock
    clock.tick(TARGET_FPS)


if __name__ == "__main__":
    before_time = pygame.time.get_ticks()
    before_sec = before_time
    game()
    pygame.quit()