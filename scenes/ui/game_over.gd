extends Control

@onready var score_label: Label = $CenterContainer/VBox/ScoreLabel
@onready var retry_button: Button = $CenterContainer/VBox/RetryButton
@onready var main_menu_button: Button = $CenterContainer/VBox/MainMenuButton


func _ready() -> void:
	score_label.text = "Final Score: %d" % GameManager.score
	retry_button.pressed.connect(_on_retry_pressed)
	main_menu_button.pressed.connect(_on_main_menu_pressed)
	retry_button.grab_focus()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _on_retry_pressed() -> void:
	SceneTransition.change_scene_with_reset("res://scenes/main/main.tscn")


func _on_main_menu_pressed() -> void:
	SceneTransition.change_scene_with_reset("res://scenes/ui/main_menu.tscn")
