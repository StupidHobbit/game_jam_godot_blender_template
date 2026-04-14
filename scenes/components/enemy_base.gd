extends CharacterBody3D
class_name EnemyBase

signal died()

@export_group("Stats")
@export var max_health: int = 30
@export var damage: int = 10
@export var score_reward: int = 50

@export_group("Movement")
@export var move_speed: float = 3.0
@export var detection_range: float = 10.0
@export var attack_range: float = 1.5
@export var attack_cooldown: float = 1.5

var health: int
var _player: Node3D
var _attack_timer: float = 0.0

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")


func _ready() -> void:
	health = max_health
	_player = get_tree().get_first_node_in_group("player")
	add_to_group("enemy")


func _physics_process(delta: float) -> void:
	_apply_gravity(delta)
	_attack_timer -= delta

	if _player:
		var dist := global_position.distance_to(_player.global_position)
		if dist <= attack_range:
			_try_attack()
		elif dist <= detection_range:
			_move_toward_player(delta)

	move_and_slide()


func take_damage(amount: int) -> void:
	health -= amount
	if health <= 0:
		_die()


func _move_toward_player(delta: float) -> void:
	var direction := ((_player.global_position - global_position) * Vector3(1, 0, 1)).normalized()
	velocity.x = direction.x * move_speed
	velocity.z = direction.z * move_speed
	look_at(Vector3(_player.global_position.x, global_position.y, _player.global_position.z))


func _try_attack() -> void:
	if _attack_timer > 0.0:
		return
	_attack_timer = attack_cooldown
	GameManager.take_damage(damage)


func _apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= _gravity * delta


func _die() -> void:
	GameManager.add_score(score_reward)
	died.emit()
	queue_free()
