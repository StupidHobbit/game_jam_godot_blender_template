extends CharacterBody3D

signal interacted(interactable: Node3D)

@export_group("Movement")
@export var walk_speed: float = 5.0
@export var sprint_speed: float = 9.0
@export var jump_velocity: float = 5.0
@export var acceleration: float = 10.0
@export var friction: float = 12.0
@export var air_control: float = 0.3

@export_group("Camera")
@export var mouse_sensitivity: float = 0.002
@export var camera_pitch_min: float = -80.0
@export var camera_pitch_max: float = 80.0

@export_group("Interaction")
@export var interact_distance: float = 2.5

@onready var camera_pivot: Node3D = $CameraPivot
@onready var camera: Camera3D = $CameraPivot/Camera3D
@onready var interact_ray: RayCast3D = $CameraPivot/Camera3D/InteractRay
@onready var animation_player: AnimationPlayer = $AnimationPlayer

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_rotate_camera(event.relative)

	if event.is_action_pressed("interact"):
		_try_interact()


func _physics_process(delta: float) -> void:
	_apply_gravity(delta)
	_handle_jump()
	_handle_movement(delta)
	move_and_slide()


func _rotate_camera(mouse_delta: Vector2) -> void:
	rotate_y(-mouse_delta.x * mouse_sensitivity)
	camera_pivot.rotate_x(-mouse_delta.y * mouse_sensitivity)
	camera_pivot.rotation.x = clamp(
		camera_pivot.rotation.x,
		deg_to_rad(camera_pitch_min),
		deg_to_rad(camera_pitch_max)
	)


func _apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= _gravity * delta


func _handle_jump() -> void:
	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = jump_velocity


func _handle_movement(delta: float) -> void:
	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	var speed := sprint_speed if Input.is_action_pressed("sprint") else walk_speed
	var blend := acceleration if is_on_floor() else acceleration * air_control

	if direction:
		velocity.x = move_toward(velocity.x, direction.x * speed, blend * delta)
		velocity.z = move_toward(velocity.z, direction.z * speed, blend * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, friction * delta)
		velocity.z = move_toward(velocity.z, 0.0, friction * delta)


func _try_interact() -> void:
	if interact_ray.is_colliding():
		var collider := interact_ray.get_collider()
		if collider is Node3D:
			interacted.emit(collider)
			if collider.has_method("interact"):
				collider.interact(self)
