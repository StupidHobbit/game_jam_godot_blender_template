extends Area3D
class_name Collectible

@export var score_value: int = 10
@export var heal_value: int = 0
@export var bob_height: float = 0.3
@export var bob_speed: float = 2.0
@export var rotation_speed: float = 1.5

var _start_y: float
var _time: float = 0.0


func _ready() -> void:
	_start_y = position.y
	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	_time += delta
	position.y = _start_y + sin(_time * bob_speed) * bob_height
	rotate_y(rotation_speed * delta)


func _on_body_entered(body: Node3D) -> void:
	if not body.is_in_group("player"):
		return

	if score_value > 0:
		GameManager.add_score(score_value)

	if heal_value > 0:
		GameManager.heal(heal_value)

	queue_free()
