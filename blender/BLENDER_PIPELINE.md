# Blender → Godot 4 Pipeline

## Пайплайн редактирования уровня в Blender

### Концепция
Уровень моделируется целиком в Blender, экспортируется одним `.gltf` файлом, затем импортируется в Godot как статическая геометрия. Интерактивные объекты (враги, триггеры, коллектиблы) расставляются поверх в Godot-сцене.

### Структура .blend файла уровня

```
level_01.blend
├── Collection: "Geometry"       ← вся статическая геометрия (пол, стены, рельеф, трава)
│   ├── floor_main               → экспортируется как level_01_geo.gltf
│   ├── walls
│   ├── ceiling
│   └── grass_surface            → инстансы собираются через depsgraph,
│       └── [Modifier] GeometryNodes: "GrassScatter"   меш экспортируется 1 раз,
│                                    в .tscn → MultiMeshInstance3D
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

> **Как скрипт различает траву от обычной геометрии?** Автоматически — по наличию модификатора типа `NODES` (Geometry Nodes). Инстансы собираются через `depsgraph.object_instances`, уникальный меш экспортируется один раз, трансформации записываются в `MultiMeshInstance3D` в `.tscn`.

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
assets/models/levels/level_01_geo.gltf       ← обычная геометрия
assets/models/levels/grass/grass_blade.gltf  ← меш травинки (один раз, без дублирования)
scenes/levels/level_01.tscn                  ← сцена с MultiMeshInstance3D для травы
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


## Трава через Geometry Nodes (модификатор)

### Концепция

Трава создаётся процедурно через модификатор **Geometry Nodes** — инстансы травинок (`grass_blade`) распределяются по поверхности пола через `Instance on Points`.

**Как скрипт экспортирует траву без дублирования геометрии:**

1. Находит объекты с модификатором `NODES` в коллекции `Geometry`
2. Итерирует `depsgraph.object_instances` — там есть все GN-инстансы с их мировыми трансформациями
3. Для каждого **уникального меша** (`grass_blade`) экспортирует `.gltf` **один раз**
4. Все трансформации инстансов записывает в `.tscn` как `MultiMeshInstance3D`

**Результат**: меш травинки хранится один раз, 1000 инстансов — это 1000 матриц в `MultiMesh`. Один draw call в Godot.

### Структура объектов

```
level_01.blend
├── Collection: "Geometry"       ← трава лежит здесь вместе с остальной геометрией
│   ├── floor_main
│   └── grass_surface            ← объект с модификатором Geometry Nodes
│       └── [Modifier] GeometryNodes: "GrassScatter"
└── Collection: "GrassAssets"    ← скрыта из рендера, только для инстансинга
    └── grass_blade              ← меш одной травинки (4–8 tri)
```

> Скрипт [`export_level.py`](export_level.py) определяет GN-объекты автоматически по наличию модификатора `NODES`. Отдельных коллекций не нужно.

### Настройка модификатора Geometry Nodes

#### 1. Создай объект-поверхность
```
Shift+A → Mesh → Plane
Масштабируй под размер уровня (S → X/Y)
Переименуй: grass_surface
Помести в коллекцию Geometry
```

#### 2. Добавь модификатор
```
Properties → Modifier Properties → Add Modifier → Generate → Geometry Nodes
Нажми "New" → переименуй нод-группу: GrassScatter
```

#### 3. Нод-граф

```
[Group Input]
      │
[Distribute Points on Faces]   ← density: 2.0–5.0 (точек/м²)
      │
[Instance on Points]           ← Instance: объект grass_blade
      ├── [Random Value] → Rotate Instances (ось Z, 0–2π)
      └── [Random Value] → Scale Instances (0.8–1.2)
      │
      ↓
[Group Output]
```

**Ключевые ноды:**

| Нод | Параметр | Значение |
|-----|----------|---------|
| `Distribute Points on Faces` | Density | 2–8 (зависит от размера уровня) |
| `Distribute Points on Faces` | Seed | любое число (для рандома) |
| `Instance on Points` | Instance | объект `grass_blade` |
| `Rotate Instances` | Rotation | `Random Value` (0, 0, 0–6.28) по Z |
| `Scale Instances` | Scale | `Random Value` (0.8–1.2) |

#### 4. Создай меш травинки (`grass_blade`)
```
Shift+A → Mesh → Plane
Удали 2 вершины → получи полоску (2 треугольника)
Вытяни вверх (E → Z) → форма травинки
Polycount: 4–8 tri на травинку
Переименуй: grass_blade
Помести в коллекцию GrassAssets
Скрой коллекцию из рендера: Collection Properties → Restrict Render (иконка камеры): off
```

#### 5. Параметры через Group Input (настраиваемые)

```
Добавь ноды Input → Group Input
Подключи к Density, Seed, Scale
```

В панели модификатора появятся слайдеры:
- **Density** — густота травы
- **Seed** — вариант распределения
- **Min/Max Scale** — разброс размеров

### Как работает экспорт

Скрипт [`export_level.py`](export_level.py) автоматически:

```python
# 1. Находит GN-объекты в коллекции Geometry
# 2. Итерирует все инстансы через depsgraph
for inst in depsgraph.object_instances:
    if inst.is_instance and inst.parent.original.name in gn_obj_names:
        # inst.object.data.name — имя меша (grass_blade)
        # inst.matrix_world    — мировая трансформация этого инстанса

# 3. Экспортирует grass_blade.gltf ОДИН РАЗ
# 4. Записывает в .tscn:
#    [sub_resource type="MultiMesh"]
#      instance_count = 1200
#      mesh = ExtResource("grass_blade_mesh")
#      instance_transforms = PackedFloat32Array(... 1200 × 12 floats ...)
#    [node type="MultiMeshInstance3D"]
#      multimesh = SubResource("...")
```

### Результат в Godot

```
level_01.tscn
├── Node3D "Level"
│   ├── [instance] Geometry      ← level_01_geo.gltf (пол, стены)
│   ├── MultiMeshInstance3D "Grass_grass_blade"
│   │     multimesh.mesh         ← assets/models/levels/grass/grass_blade.gltf (1 раз)
│   │     multimesh.instance_count = 1200
│   │     multimesh.instance_transforms = [...]  ← 1200 трансформаций
│   └── ... props, markers
```

`MultiMeshInstance3D` рендерит все 1200 травинок за **один draw call**.

### Оптимизация травы

| Приём | Описание |
|-------|---------|
| **Density Map** | Подключи текстуру ч/б к Density — трава только там, где нужно |
| **Polycount травинки** | 4–8 tri — меш хранится один раз, polycount не умножается |
| **Vertex Colors** | Используй `Set Material` + Vertex Color для вариативности цвета |
| **Несколько вариантов** | Несколько мешей (`grass_blade_a`, `grass_blade_b`) → несколько `MultiMesh` |

### Рекомендуемые настройки для game jam

```
Размер уровня:      20×20 м
Density:            3.0 точки/м²  →  ~1200 инстансов
Polycount/blade:    6 tri
Меш в .gltf:        6 tri (один раз)
Трансформации:      1200 × 12 float = ~57 КБ в .tscn
Draw calls:         1 (MultiMeshInstance3D)  ✓
```

### Чеклист для травы

- [ ] Объект `grass_surface` находится в коллекции `Geometry`
- [ ] Модификатор Geometry Nodes добавлен на `grass_surface`
- [ ] Объект `grass_blade` в коллекции `GrassAssets` с отключённым рендером
- [ ] Применены трансформации на `grass_surface` (`Ctrl+A → All Transforms`)
- [ ] Скрипт запущен — в логе строка `[OK] Grass mesh 'grass_blade': N instance(s)`
- [ ] В Godot в сцене появился узел `MultiMeshInstance3D` с травой

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
