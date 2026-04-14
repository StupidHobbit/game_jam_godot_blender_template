# 🎮 Game Jam 3D Template — Godot 4

Готовая заготовка для быстрого создания 3D игры на хакатоне. Включает полный пайплайн от Blender до Godot.

---

## 🚀 Быстрый старт

### Требования
- [Godot 4.3+](https://godotengine.org/download)
- [Blender 4.x](https://www.blender.org/download/) (для 3D моделей)

### Запуск
1. Открой `project.godot` в Godot 4
2. Нажми **F5** или кнопку Play
3. Стартовая сцена — `scenes/main/main.tscn`

---

## 📁 Структура проекта

```
jam/
├── project.godot              ← конфигурация проекта
├── autoload/                  ← синглтоны (автозагрузка)
│   ├── game_manager.gd        ← счёт, здоровье, пауза, события
│   ├── audio_manager.gd       ← музыка, SFX, 3D-звук
│   └── scene_transition.gd    ← переходы между сценами (fade)
├── scenes/
│   ├── main/
│   │   ├── main.tscn          ← главная игровая сцена
│   │   └── main.gd
│   ├── player/
│   │   ├── player.tscn        ← персонаж (FPS-контроллер)
│   │   └── player.gd
│   ├── camera/
│   │   └── follow_camera.gd   ← камера от третьего лица
│   ├── components/
│   │   ├── interactable.gd    ← базовый класс интерактивных объектов
│   │   ├── collectible.gd     ← подбираемые предметы
│   │   └── enemy_base.gd      ← базовый класс врага
│   └── ui/
│       ├── hud.gd             ← HUD (здоровье, счёт, подсказки)
│       ├── main_menu.gd       ← главное меню
│       ├── pause_menu.gd      ← меню паузы
│       └── game_over.gd       ← экран конца игры
├── assets/
│   ├── models/                ← .gltf модели из Blender
│   │   ├── characters/
│   │   ├── enemies/
│   │   ├── props/
│   │   └── environment/
│   ├── textures/              ← текстуры
│   └── audio/
│       ├── music/
│       └── sfx/
└── blender/
    ├── export_to_godot.py     ← скрипт экспорта из Blender
    └── BLENDER_PIPELINE.md    ← полное руководство по пайплайну
```

---

## 🎮 Управление (по умолчанию)

| Действие | Клавиша |
|----------|---------|
| Движение | WASD / Стрелки |
| Прыжок | Пробел |
| Спринт | Shift |
| Взаимодействие | E |
| Пауза | Escape |
| Камера | Мышь |
| Зум камеры | Колёсико мыши |

---

## 🔧 Синглтоны

### `GameManager`
Центральный менеджер состояния игры.

```gdscript
GameManager.add_score(10)
GameManager.take_damage(25)
GameManager.heal(10)
GameManager.toggle_pause()
GameManager.trigger_game_over()
GameManager.trigger_level_complete()

# Сигналы
GameManager.score_changed.connect(func(score): ...)
GameManager.health_changed.connect(func(hp, max_hp): ...)
GameManager.game_over.connect(func(): ...)
```

### `AudioManager`
```gdscript
AudioManager.play_music(preload("res://assets/audio/music/theme.ogg"))
AudioManager.stop_music()
AudioManager.play_sfx(preload("res://assets/audio/sfx/jump.wav"))
AudioManager.play_sfx_3d(stream, global_position)
AudioManager.music_volume = 0.8
AudioManager.sfx_volume = 1.0
```

### `SceneTransition`
```gdscript
SceneTransition.change_scene("res://scenes/main/main.tscn")
SceneTransition.change_scene_with_reset("res://scenes/main/main.tscn")
await SceneTransition.transition_finished
```

---

## 🧩 Компоненты

### `Interactable` (Area3D)
Добавь к любому объекту для взаимодействия по клавише E:
```gdscript
var door := Interactable.new()
door.hint_text = "Открыть дверь"
door.single_use = true
door.on_interact.connect(func(player): open_door())
```

### `Collectible` (Area3D)
Подбираемый предмет с анимацией боббинга:
```gdscript
@export var score_value: int = 10
@export var heal_value: int = 0
```

### `EnemyBase` (CharacterBody3D)
Базовый враг с патрулированием и атакой:
```gdscript
class_name MyEnemy extends EnemyBase

func _die() -> void:
    # Кастомная логика смерти
    super._die()
```

---

## 🎥 Камеры

### FPS (встроена в Player)
Уже настроена в `player.tscn`. Управление мышью, взаимодействие через RayCast.

### Third-Person (`follow_camera.gd`)
Добавь `Camera3D` с этим скриптом в сцену:
```gdscript
@export var target: Node3D  # ← укажи Player
@export var distance: float = 5.0
```
Поддерживает: коллизию с окружением, зум колёсиком, инверсию Y.

---

## 🎨 Blender Pipeline

Полное руководство: [`blender/BLENDER_PIPELINE.md`](blender/BLENDER_PIPELINE.md)

### Быстрый экспорт
```bash
blender --background my_model.blend --python blender/export_to_godot.py
```

### Ключевые правила
- 1 Blender unit = 1 метр
- Применяй трансформации перед экспортом (`Ctrl+A`)
- Формат: **glTF Separate** (`.gltf` + `.bin` + `textures/`)
- Анимации — отдельные Actions в NLA Editor

---

## ⚡ Советы для хакатона

1. **День 1**: Механика + уровень-прототип + базовые ассеты
2. **День 2**: Контент + враги/препятствия + звук
3. **День 3**: Полировка + UI + баг-фикс + билд

### Быстрые победы
- Используй `WorldEnvironment` с `ProceduralSkyMaterial` — бесплатное небо
- `GPUParticles3D` для эффектов без арта
- Vertex Colors в Blender вместо текстур — быстро и красиво
- `AudioStreamRandomizer` для вариативных SFX

---

## 📦 Сборка (Export)

1. `Project → Export → Add Preset` (Windows/Mac/Linux/Web)
2. Скачай export templates: `Editor → Manage Export Templates`
3. `Export Project` → выбери папку

Для Web (itch.io): выбери `Web` пресет, экспортируй в папку `build/web/`.
