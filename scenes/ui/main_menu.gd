extends Control

@onready var play_button: Button = $CenterContainer/VBox/PlayButton
@onready var quit_button: Button = $CenterContainer/VBox/QuitButton
@onready var title_label: Label = $CenterContainer/VBox/TitleLabel


func _ready() -> void:
	play_button.pressed.connect(_on_play_pressed)
	quit_button.pressed.connect(_on_quit_pressed)
	play_button.grab_focus()


func _on_play_pressed() -> void:
	SceneTransition.change_scene_with_reset("res://scenes/main/main.tscn")


func _on_quit_pressed() -> void:
	get_tree().quit()
