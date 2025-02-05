import pygame

import random
import json
import os
import sqlite3
from datetime import datetime

# Инициализация Pygame
pygame.init()

# Константы
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
# Размер персонажа
PLAYER_SIZE = (50, 50)
# Размер врага
ENEMY_SIZE = (50, 50)
# Желаемый размер снаряда
BULLET_SIZE = (20, 20)
# Появление врагов каждые 100 кадров (ускорено)
ENEMY_SPAWN_RATE = 100
PLAYER_HEALTH = 100
ENEMY_HEALTH = 10
SCORE_PER_KILL = 5
COINS_PER_KILL = 5
HOME_WIDTH = 100
HOME_DAMAGE = 20
NO_COOLDOWN_COST = 25
NO_COOLDOWN_DURATION = 600
BULLET_COOLDOWN = 24  # Кулдаун на стрельбу в кадрах
LEVELS = [
    {"PLAYER_SPEED": 4, "BULLET_SPEED": 7, "ENEMY_SPEED": 2, "ENEMY_DAMAGE": 10, "TURRET_DAMAGE": 5, "BARRIERS": 3,
     "ENEMY_SPAWN_RATE": 100},
    {"PLAYER_SPEED": 5, "BULLET_SPEED": 8, "ENEMY_SPEED": 3, "ENEMY_DAMAGE": 15, "TURRET_DAMAGE": 4, "BARRIERS": 4,
     "ENEMY_SPAWN_RATE": 80},
    {"PLAYER_SPEED": 6, "BULLET_SPEED": 9, "ENEMY_SPEED": 4, "ENEMY_DAMAGE": 20, "TURRET_DAMAGE": 3, "BARRIERS": 2,
     "ENEMY_SPAWN_RATE": 60},
]

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

if os.path.exists("game_progress.db"):
    ...
else:
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                score INTEGER,
                coins INTEGER,
                game_time REAL,
                save_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    cursor.execute('INSERT INTO progress (score, coins, game_time) VALUES (?, ?, ?)', (0, 0, 0))
    conn.commit()
    conn.close()

# Загрузка изображений
player_image = pygame.image.load('IMG/player.png')
enemy_images = [
    pygame.image.load('IMG/enemy1.png'),
    pygame.image.load('IMG/enemy2.png'),
    pygame.image.load('IMG/enemy3.png'),
    pygame.image.load('IMG/enemy4.png')
]
bullet_image = pygame.image.load('IMG/bullet.png')
explosion_image = pygame.image.load('IMG/explosion.png')
barrier_image = pygame.image.load('IMG/barrier.png')
background_image = pygame.image.load('IMG/background.png')
menu_background_image = pygame.image.load('IMG/menu_background.png')
game_over_background_image = pygame.image.load('IMG/game_over_background.png')

# Масштабирование изображений
player_image = pygame.transform.scale(player_image, PLAYER_SIZE)
enemy_images = [pygame.transform.scale(img, ENEMY_SIZE) for img in enemy_images]
bullet_image = pygame.transform.scale(bullet_image, BULLET_SIZE)
explosion_image = pygame.transform.scale(explosion_image, (50, 50))
barrier_image = pygame.transform.scale(barrier_image, (50, 50))
background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
menu_background_image = pygame.transform.scale(menu_background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
game_over_background_image = pygame.transform.scale(game_over_background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

# Загрузка звуков
shoot_sound = pygame.mixer.Sound('Sounds/shoot.mp3')
explosion_sound = pygame.mixer.Sound('Sounds/explosion.mp3')
hit_sound = pygame.mixer.Sound('Sounds/shoot.mp3')

# Создание экрана
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Защита крепости')


# Класс игрока
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = player_image
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.health = PLAYER_HEALTH
        self.coins = 0
        self.no_cooldown_timer = 0
        self.bullet_cooldown = 0

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_d]:
            self.rect.x += PLAYER_SPEED
        if keys[pygame.K_w]:
            self.rect.y -= PLAYER_SPEED
        if keys[pygame.K_s]:
            self.rect.y += PLAYER_SPEED

        # Ограничение движения по экрану
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

        # Способность стрелять без кулдауна
        if self.no_cooldown_timer > 0:
            self.no_cooldown_timer -= 1

        # Кулдаун на стрельбу
        if self.bullet_cooldown > 0:
            self.bullet_cooldown -= 1

    def apply_no_cooldown(self):
        if self.coins >= NO_COOLDOWN_COST:
            self.coins -= NO_COOLDOWN_COST
            self.no_cooldown_timer = NO_COOLDOWN_DURATION

    def shoot(self, target_pos):
        if self.no_cooldown_timer > 0:
            bullet = Bullet(self.rect.center, target_pos)
            all_sprites.add(bullet)
            bullets.add(bullet)
            shoot_sound.play()
        else:
            if self.bullet_cooldown == 0:
                bullet = Bullet(self.rect.center, target_pos)
                all_sprites.add(bullet)
                bullets.add(bullet)
                shoot_sound.play()
                self.bullet_cooldown = BULLET_COOLDOWN


# Класс врага
class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = random.choice(enemy_images)
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_WIDTH
        self.rect.y = random.randint(0, SCREEN_HEIGHT - self.rect.height)
        self.health = ENEMY_HEALTH
        # Разная скорость ходьбы
        self.speed = random.uniform(2, 4)

    def update(self):
        self.rect.x -= self.speed
        if self.rect.right < 0:
            self.kill()


# Класс снаряда
class Bullet(pygame.sprite.Sprite):
    def __init__(self, start_pos, target_pos):
        super().__init__()
        self.image = bullet_image
        self.rect = self.image.get_rect()
        self.rect.center = start_pos
        self.target_pos = target_pos
        self.direction = pygame.math.Vector2(target_pos) - pygame.math.Vector2(start_pos)
        self.direction.normalize_ip()

    def update(self):
        self.rect.x += self.direction.x * BULLET_SPEED
        self.rect.y += self.direction.y * BULLET_SPEED
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or self.rect.bottom < 0 or \
                self.rect.top > SCREEN_HEIGHT:
            self.kill()


# Класс взрыва
class Explosion(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        # Время продления взрыва в кадрах
        self.image = explosion_image
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.lifetime = 10

    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


# Класс барьера
class Barrier(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = barrier_image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


# Загрузка лучшего результата из файла
def load_best_score():
    if os.path.exists('best_score.json'):
        with open('best_score.json', 'r') as file:
            return json.load(file).get('best_score', 0)
    return 0


# Сохранение лучшего результата в файл
def save_best_score(score):
    best_score = load_best_score()
    if score > best_score:
        with open('best_score.json', 'w') as file:
            json.dump({'best_score': score}, file)


# Сохранение прогресса в базу данных
def save_progress(score, coins, game_time):
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER,
            coins INTEGER,
            game_time REAL,
            save_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('INSERT INTO progress (score, coins, game_time) VALUES (?, ?, ?)',
                   (score, coins, game_time))
    conn.commit()
    conn.close()


# Отображение данных из базы данных
def show_progress():
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM progress')
    rows = cursor.fetchall()
    conn.close()

    font = pygame.font.Font(None, 36)
    header_text = font.render('ID | Score   | Coins   | Time (min)  |         Save Time', True, BLACK)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return

        screen.fill((52, 167, 46))
        screen.blit(header_text, (10, 10))
        y_offset = 50
        for row in rows:
            text = font.render(f'{row[0]:<3} | {row[1]:<9.2f} | {row[2]:<9.2f} | {row[3]:<15.2f} | {row[4]:<5}',
                               True,
                               BLACK)
            screen.blit(text, (10, y_offset))
            y_offset += 40

        pygame.display.flip()


# Функция для отображения главного меню
def main_menu():
    font = pygame.font.Font(None, 74)
    level_texts = [
        font.render('Лёгкий', True, BLACK),
        font.render('Средний', True, BLACK),
        font.render('Сложный', True, BLACK)

    ]

    level_rects = [
        pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50, 200, 50),
        pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2, 200, 50),
        pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 50, 200, 50)
    ]

    progress_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 100, 200, 50)
    font.render(' ', True, BLACK)
    progress_text = font.render('* Прогресс *', True, BLACK)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for i, rect in enumerate(level_rects):
                    if rect.collidepoint(mouse_pos):
                        return i
                if progress_button.collidepoint(mouse_pos):
                    show_progress()

        screen.blit(menu_background_image, (0, 0))
        for i, text in enumerate(level_texts):
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 50 + i * 50))
        screen.blit(progress_text, (SCREEN_WIDTH // 2 - progress_text.get_width() // 2, SCREEN_HEIGHT // 2 + 100))

        pygame.display.flip()


# Отображение финального окна
def game_over_screen(score, coins, game_time):
    font = pygame.font.Font(None, 74)
    score_text = font.render(f'Счет: {score}', True, BLACK)
    coins_text = font.render(f'Монеты: {coins}', True, GREEN)
    time_text = font.render(f'Время: {game_time:.2f} минут', True, BLACK)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return

        screen.blit(game_over_background_image, (0, 0))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 200))
        screen.blit(coins_text, (SCREEN_WIDTH // 2 - coins_text.get_width() // 2, 250))
        screen.blit(time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, 300))

        pygame.display.flip()


# Основная функция игры
def main():
    global PLAYER_SPEED, BULLET_SPEED, ENEMY_SPEED, ENEMY_DAMAGE, TURRET_DAMAGE, ENEMY_SPAWN_RATE
    level = main_menu()
    if level is None:
        return

    PLAYER_SPEED, BULLET_SPEED, ENEMY_SPEED, ENEMY_DAMAGE, TURRET_DAMAGE, BARRIERS, ENEMY_SPAWN_RATE = LEVELS[
        level].values()

    clock = pygame.time.Clock()
    running = True
    paused = False

    global all_sprites, bullets, enemies, explosions, barriers
    all_sprites = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    explosions = pygame.sprite.Group()
    barriers = pygame.sprite.Group()

    player = Player()
    all_sprites.add(player)

    enemy_spawn_timer = 0
    score = 0
    best_score = load_best_score()
    home_damage_timer = 0
    start_time = datetime.now()
    barrier_move_timer = 0

    # Генерация барьеров
    for _ in range(BARRIERS):
        x = random.randint(150, SCREEN_WIDTH - 50)
        y = random.randint(50, SCREEN_HEIGHT - 50)
        barrier = Barrier(x, y)
        all_sprites.add(barrier)
        barriers.add(barrier)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_2:
                    player.apply_no_cooldown()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not paused:
                    mouse_pos = pygame.mouse.get_pos()
                    # Левая кнопка мыши для стрельбы
                    if event.button == 1:
                        player.shoot(mouse_pos)

        # Игровой процесс вне паузы
        if not paused:
            enemy_spawn_timer += 1
            if enemy_spawn_timer >= ENEMY_SPAWN_RATE:
                enemy = Enemy()
                all_sprites.add(enemy)
                enemies.add(enemy)
                enemy_spawn_timer = 0

            all_sprites.update()

            # Проверка столкновений снарядов с врагами
            for bullet in bullets:
                enemy_hit_list = pygame.sprite.spritecollide(bullet, enemies, False)
                for enemy in enemy_hit_list:
                    enemy.health -= TURRET_DAMAGE
                    if enemy.health <= 0:
                        enemy.kill()
                        score += SCORE_PER_KILL
                        player.coins += COINS_PER_KILL
                        explosion = Explosion(enemy.rect.center)
                        all_sprites.add(explosion)
                        explosions.add(explosion)
                        explosion_sound.play()
                    bullet.kill()

            # Проверка столкновений игрока с врагами
            if pygame.sprite.spritecollideany(player, enemies):
                player.health -= ENEMY_DAMAGE
                hit_sound.play()
                if player.health <= 0:
                    save_best_score(score)
                    game_time = (datetime.now() - start_time).total_seconds() / 60
                    save_progress(score, player.coins, game_time)
                    game_over_screen(score, player.coins, game_time)
                    running = False

            # Проверка столкновений врагов с левой стеной
            for enemy in enemies:
                if enemy.rect.right <= 0:
                    player.health -= HOME_DAMAGE
                    hit_sound.play()
                    if player.health <= 0:
                        save_best_score(score)
                        game_time = (datetime.now() - start_time).total_seconds() / 60
                        save_progress(score, player.coins, game_time)
                        game_over_screen(score, player.coins, game_time)
                        running = False

            # Проверка столкновений с барьерами
            for barrier in barriers:
                if pygame.sprite.collide_rect(player, barrier):
                    player.rect.x = player.rect.x - PLAYER_SPEED if player.rect.x > barrier.rect.x \
                        else player.rect.x + PLAYER_SPEED
                    player.rect.y = player.rect.y - PLAYER_SPEED if player.rect.y > barrier.rect.y \
                        else player.rect.y + PLAYER_SPEED
                for enemy in enemies:
                    if pygame.sprite.collide_rect(enemy, barrier):
                        enemy.rect.x = enemy.rect.x - enemy.speed if enemy.rect.x > barrier.rect.x \
                            else enemy.rect.x + enemy.speed
                        enemy.rect.y = enemy.rect.y - enemy.speed if enemy.rect.y > barrier.rect.y \
                            else enemy.rect.y + enemy.speed

            # Создание барьеров на сложном уровне каждые 15 секунд
            if level == 2:
                barrier_move_timer += 1
                if barrier_move_timer >= 900:
                    barriers.empty()
                    for _ in range(BARRIERS):
                        x = random.randint(150, SCREEN_WIDTH - 50)
                        y = random.randint(50, SCREEN_HEIGHT - 50)
                        barrier = Barrier(x, y)
                        all_sprites.add(barrier)
                        barriers.add(barrier)
                    barrier_move_timer = 0

            # Проверка координат врагов
            for enemy in enemies:
                if 0 <= enemy.rect.x <= 5 and 0 <= enemy.rect.y <= 800:
                    enemy.kill()
                    player.health -= HOME_DAMAGE
                    hit_sound.play()
                    if player.health <= 0:
                        save_best_score(score)
                        game_time = (datetime.now() - start_time).total_seconds() / 60
                        save_progress(score, player.coins, game_time)
                        game_over_screen(score, player.coins, game_time)
                        running = False

            screen.blit(background_image, (0, 0))
            all_sprites.draw(screen)

            # Отображение здоровья игрока, счета и монет
            font = pygame.font.Font(None, 36)
            health_text = font.render(f'Здоровье: {player.health}', True, RED)
            score_text = font.render(f'Счет: {score}', True, BLACK)
            best_score_text = font.render(f'Лучший счет: {best_score}', True, BLACK)
            coins_text = font.render(f'Монеты: {player.coins}', True, GREEN)
            screen.blit(health_text, (10, 10))
            screen.blit(score_text, (10, 50))
            screen.blit(best_score_text, (10, 90))
            screen.blit(coins_text, (10, 130))

            pygame.display.flip()
            clock.tick(60)

        else:
            # Отображение паузы
            font = pygame.font.Font(None, 74)
            pause_text = font.render('П А У З А', True, BLACK)
            screen.blit(pause_text, (
                SCREEN_WIDTH // 2 - pause_text.get_width() // 2,
                SCREEN_HEIGHT // 2 - pause_text.get_height() // 2))
            pygame.display.flip()
            clock.tick(10)

    pygame.quit()


if __name__ == "__main__":
    main()
