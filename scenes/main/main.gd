extends Node3D


func _ready() -> void:
	GameManager.reset()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
