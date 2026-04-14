extends Control

@onready var resume_button: Button = $PanelContainer/VBox/ResumeButton
@onready var main_menu_button: Button = $PanelContainer/VBox/MainMenuButton
@onready var quit_button: Button = $PanelContainer/VBox/QuitButton


func _ready() -> void:
	resume_button.pressed.connect(_on_resume_pressed)
	main_menu_button.pressed.connect(_on_main_menu_pressed)
	quit_button.pressed.connect(_on_quit_pressed)


func _on_resume_pressed() -> void:
	GameManager.toggle_pause()


func _on_main_menu_pressed() -> void:
	GameManager.toggle_pause()
	SceneTransition.change_scene_with_reset("res://scenes/ui/main_menu.tscn")


func _on_quit_pressed() -> void:
	get_tree().quit()
