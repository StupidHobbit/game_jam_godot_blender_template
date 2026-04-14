extends CanvasLayer

@onready var health_bar: ProgressBar = $MarginContainer/VBox/HealthBar
@onready var score_label: Label = $MarginContainer/VBox/ScoreLabel
@onready var crosshair: TextureRect = $Crosshair
@onready var interact_hint: Label = $InteractHint
@onready var pause_menu: Control = $PauseMenu


func _ready() -> void:
	GameManager.health_changed.connect(_on_health_changed)
	GameManager.score_changed.connect(_on_score_changed)
	GameManager.game_paused.connect(_on_game_paused)
	GameManager.game_over.connect(_on_game_over)

	health_bar.max_value = GameManager.max_health
	health_bar.value = GameManager.health
	score_label.text = "Score: 0"
	pause_menu.hide()
	interact_hint.hide()


func show_interact_hint(text: String = "Press E to interact") -> void:
	interact_hint.text = text
	interact_hint.show()


func hide_interact_hint() -> void:
	interact_hint.hide()


func _on_health_changed(new_health: int, max_health: int) -> void:
	health_bar.max_value = max_health
	var tween := create_tween()
	tween.tween_property(health_bar, "value", new_health, 0.2)


func _on_score_changed(new_score: int) -> void:
	score_label.text = "Score: %d" % new_score


func _on_game_paused(is_paused: bool) -> void:
	pause_menu.visible = is_paused
	if is_paused:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	else:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _on_game_over() -> void:
	SceneTransition.change_scene("res://scenes/ui/game_over.tscn")
