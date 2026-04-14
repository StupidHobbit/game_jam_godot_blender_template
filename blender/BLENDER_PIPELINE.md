# Blender → Godot 4 Pipeline

## Пайплайн редактирования уровня в Blender

### Концепция
Уровень моделируется целиком в Blender, экспортируется одним `.gltf` файлом, затем импортируется в Godot как статическая геометрия. Интерактивные объекты (враги, триггеры, коллектиблы) расставляются поверх в Godot-сцене.

### Структура .blend файла уровня

```
level_01.blend
├── Collection: "Geometry"       ← уникальная статическая геометрия (пол, стены, рельеф)
│   ├── floor_main               → экспортируется ОДИН РАЗ как level_01_geo.gltf
│   ├── walls
│   └── ceiling
├── Collection: "Props"          ← повторяющиеся пропсы
│   ├── tree (оригинал)          → экспортируется ОДИН РАЗ как props/tree.gltf
│   ├── tree.001 (Alt+D копия)   → только Transform в .tscn, меш не дублируется
│   ├── tree.002 (Alt+D копия)   → только Transform в .tscn
│   ├── barrel (оригинал)        → экспортируется ОДИН РАЗ как props/barrel.gltf
│   └── barrel.001 (Alt+D копия)
└── Collection: "Markers"        ← Empty-объекты как маркеры спавна
    ├── spawn_player             ← Custom Property: type = "player_spawn"
    ├── spawn_enemy_01           ← Custom Property: type = "enemy_spawn"
    └── trigger_level_end        ← Custom Property: type = "trigger"
```

### ⚠️ Linked Duplicates — ключевое правило для пропсов

| Операция | Результат | Использовать для |
|----------|-----------|-----------------|
| **Alt+D** | Linked Duplicate — общий меш, разные трансформации | Пропсы (деревья, бочки, камни) ✅ |
| Shift+D | Copy — отдельный меш, данные дублируются | Уникальные объекты ✅ |

`export_level.py` группирует объекты по `obj.data.name` — все объекты с одинаковым мешем (Alt+D) экспортируются **один раз**, а в `.tscn` добавляются только их трансформации.

**Итог**: 50 деревьев = 1 `.gltf` файл + 50 строк Transform в `.tscn` (не 50 копий геометрии).

### Правила геометрии уровня

1. **Один материал = один меш** (по возможности) — меньше draw calls
2. **Используй Atlas-текстуру** для всей геометрии уровня
3. **Origin уровня = (0, 0, 0)** — не двигай весь уровень, только отдельные объекты
4. **Масштаб**: 1 клетка пола = 1×1 метр
5. **Коллизия**: для уровня используй `Trimesh` в Godot (точная, статичная)

### Маркеры спавна (Empty объекты)

В Blender создай Empty (`Shift+A → Empty → Plain Axes`) для каждой точки спавна:

```
Object Properties → Custom Properties:
  type = "player_spawn"    → точка старта игрока
  type = "enemy_spawn"     → точка спавна врага
  type = "collectible"     → точка спавна предмета
  type = "trigger"         → триггерная зона
  scene = "res://scenes/components/enemy_base.tscn"  → какую сцену инстанцировать
```

Скрипт `export_level.py` читает эти маркеры и генерирует `.tscn` файл с правильными позициями.

### Экспорт уровня

```bash
# Экспорт геометрии + генерация .tscn с маркерами
blender --background level_01.blend --python blender/export_level.py
```

Результат:
```
assets/models/levels/level_01.gltf    ← геометрия
scenes/levels/level_01.tscn           ← готовая сцена Godot с маркерами
```

### Импорт в Godot

1. Godot автоматически импортирует `level_01.gltf`
2. Открой `scenes/levels/level_01.tscn` — геометрия уже подключена
3. Настрой коллизию: выдели `MeshInstance3D` → `Mesh → Create Trimesh Static Body`
4. Расставь врагов/триггеры по маркерам (или используй сгенерированный `.tscn`)

### Итерационный процесс

```
Blender (редактируй) → export_level.py → Godot (F5 тест) → повтор
```

- Godot автоматически перезагружает изменённые `.gltf` файлы
- Не нужно пересоздавать сцену — только переэкспортируй геометрию
- Маркеры пересоздаются скриптом автоматически

---


## Настройка Blender

### Версия
- Blender **4.x** (рекомендуется последняя стабильная)
- Godot **4.3+**

### Единицы измерения
- `Scene Properties → Units → Unit System: Metric`
- `Unit Scale: 1.0`
- 1 Blender unit = 1 метр в Godot

### Оси координат
Blender и Godot используют разные системы координат. Экспортёр glTF конвертирует автоматически:
- Blender Y-up → Godot Y-up ✓ (флаг `export_yup=True`)

---

## Правила моделирования

### Именование объектов
```
player_body          → персонаж
enemy_goblin         → враг
prop_barrel          → реквизит
env_rock_01          → окружение
weapon_sword         → оружие
```

### Трансформации
- Перед экспортом всегда применяй: `Ctrl+A → All Transforms`
- Origin объекта = точка привязки в Godot (ставь в основание для персонажей)

### Полигональность (game jam)
| Тип объекта | Рекомендуемый polycount |
|-------------|------------------------|
| Главный герой | 500–2000 tri |
| Враг | 300–1500 tri |
| Prop (крупный) | 100–500 tri |
| Prop (мелкий) | 50–200 tri |
| Окружение (тайл) | 50–300 tri |

### UV-развёртка
- Используй `Smart UV Project` для быстрой развёртки
- Для тайловых текстур — `Unwrap` с правильными швами
- Margin между островами: **0.02–0.05**

---

## Материалы и текстуры

### Принципы (game jam speed)
1. **Vertex Colors** — самый быстрый способ, без текстур
2. **Atlas-текстура** — одна текстура 512×512 или 1024×1024 на все объекты
3. **PBR (Principled BSDF)** — экспортируется корректно в glTF

### Текстурные карты для glTF
| Карта | Назначение |
|-------|-----------|
| Base Color | Albedo / диффузный цвет |
| Metallic-Roughness | Металличность + шероховатость (в одной текстуре) |
| Normal Map | Нормали (OpenGL-формат, Godot конвертирует) |
| Emission | Свечение |

### Bake (если нужно)
```
Edit → Preferences → Add-ons → Bake Wrangler (опционально)
Render → Bake → Diffuse / Normal / AO
```

---

## Анимации

### Настройка арматуры
- Имя арматуры: `Armature` (или название персонажа)
- Кости именуй по стандарту: `spine`, `head`, `arm_L`, `arm_R`, `leg_L`, `leg_R`
- Используй **Pose Mode** для создания поз

### NLA Editor (Non-Linear Animation)
Каждая анимация должна быть отдельным **Action** в NLA:
```
idle        → петлевая анимация ожидания
walk        → петлевая анимация ходьбы
run         → петлевая анимация бега
jump        → анимация прыжка (не петлевая)
attack      → анимация атаки
death       → анимация смерти
```

### Экспорт анимаций
- `Export → glTF → Animation → NLA Strips: ✓`
- `Optimize Animation: ✓`

---

## Экспорт в Godot

### Способ 1: Скрипт (рекомендуется)
```bash
# Экспорт всех мешей из .blend файла
blender --background my_model.blend --python blender/export_to_godot.py

# Или открой Blender → Scripting → Run Script
```

### Способ 2: Ручной экспорт
```
File → Export → glTF 2.0 (.gltf/.glb)

Настройки:
✓ Format: glTF Separate (.gltf + .bin + textures)
✓ Apply Modifiers
✓ Y Up
✓ Export Selected Objects (если нужно)
✓ Animations → NLA Strips
✓ Optimize Animation Size
```

### Куда сохранять
```
assets/
  models/
    characters/    ← персонажи (.gltf + .bin + textures/)
    enemies/       ← враги
    props/         ← реквизит
    environment/   ← окружение, тайлы
  textures/        ← отдельные текстуры
  audio/
    music/
    sfx/
```

---

## Импорт в Godot

### Автоматический импорт
Godot автоматически импортирует `.gltf` файлы при помещении в папку `assets/`.

### Настройки импорта (Import dock)
```
Meshes → Generate LODs: ✓ (для оптимизации)
Animation → Import: ✓
Animation → Storage: Files (.res)
Materials → Storage: Files (.tres)  ← позволяет редактировать материалы
```

### Создание сцены из модели
1. Перетащи `.gltf` в viewport → `New Inherited Scene`
2. Сохрани как `.tscn` в `scenes/`
3. Добавь коллизию: `Mesh → Create Trimesh Static Body` или `Create Convex Static Body`

### Коллизия
| Тип | Когда использовать |
|-----|-------------------|
| `Trimesh` | Статичные объекты окружения (точная) |
| `Convex` | Динамические объекты, подбираемые предметы |
| `Box/Capsule/Sphere` | Персонажи, враги (быстрая) |

---

## Кастомные свойства объекта (Custom Properties)

В Blender можно задать свойства, которые передаются в Godot через glTF extras:

```
Object Properties → Custom Properties → Add:
  godot_category = "props"     → папка экспорта
  godot_group = "enemy"        → группа в Godot
  godot_layer = 2              → физический слой
```

---

## Чеклист перед экспортом

- [ ] Применены все трансформации (`Ctrl+A → All Transforms`)
- [ ] Применены все модификаторы
- [ ] UV-развёртка корректна (нет перекрытий для lightmap)
- [ ] Нормали направлены наружу (`Overlay → Face Orientation` — всё синее)
- [ ] Материалы используют Principled BSDF
- [ ] Анимации разбиты по Actions в NLA Editor
- [ ] Origin объекта в правильном месте
- [ ] Polycount в пределах нормы
- [ ] Файл сохранён перед экспортом
