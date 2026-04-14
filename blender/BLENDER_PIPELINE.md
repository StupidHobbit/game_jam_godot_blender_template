# Blender → Godot 4 Pipeline

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
