extends Node

signal game_paused(is_paused: bool)
signal score_changed(new_score: int)
signal health_changed(new_health: int, max_health: int)
signal game_over()
signal level_completed()

const MAIN_MENU_SCENE := "res://scenes/ui/main_menu.tscn"
const GAME_SCENE := "res://scenes/main/main.tscn"

var score: int = 0
var health: int = 100
var max_health: int = 100
var is_paused: bool = false
var current_level: int = 1


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		toggle_pause()


func toggle_pause() -> void:
	is_paused = !is_paused
	get_tree().paused = is_paused
	game_paused.emit(is_paused)


func add_score(amount: int) -> void:
	score += amount
	score_changed.emit(score)


func take_damage(amount: int) -> void:
	health = clamp(health - amount, 0, max_health)
	health_changed.emit(health, max_health)
	if health <= 0:
		trigger_game_over()


func heal(amount: int) -> void:
	health = clamp(health + amount, 0, max_health)
	health_changed.emit(health, max_health)


func trigger_game_over() -> void:
	game_over.emit()


func trigger_level_complete() -> void:
	level_completed.emit()
	current_level += 1


func reset() -> void:
	score = 0
	health = max_health
	is_paused = false
	get_tree().paused = false
