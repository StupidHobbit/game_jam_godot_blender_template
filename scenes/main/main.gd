extends Node3D

@onready var player: CharacterBody3D = $Player
@onready var hud: CanvasLayer = $HUD


func _ready() -> void:
	GameManager.reset()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
