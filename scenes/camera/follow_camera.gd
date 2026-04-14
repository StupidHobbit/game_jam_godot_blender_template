extends Camera3D

@export_group("Target")
@export var target: Node3D
@export var target_offset: Vector3 = Vector3(0, 1.5, 0)

@export_group("Distance")
@export var distance: float = 5.0
@export var min_distance: float = 1.5
@export var max_distance: float = 10.0

@export_group("Rotation")
@export var mouse_sensitivity: float = 0.003
@export var pitch_min: float = -40.0
@export var pitch_max: float = 70.0
@export var invert_y: bool = false

@export_group("Smoothing")
@export var position_smoothing: float = 8.0
@export var rotation_smoothing: float = 10.0

@export_group("Collision")
@export var collision_margin: float = 0.2
@export var collision_mask: int = 1

var _yaw: float = 0.0
var _pitch: float = 20.0
var _current_distance: float = 0.0


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	top_level = true
	_current_distance = distance


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_yaw -= event.relative.x * mouse_sensitivity
		var pitch_delta := event.relative.y * mouse_sensitivity
		_pitch += pitch_delta if invert_y else -pitch_delta
		_pitch = clamp(_pitch, pitch_min, pitch_max)

	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clamp(distance - 0.5, min_distance, max_distance)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clamp(distance + 0.5, min_distance, max_distance)


func _physics_process(delta: float) -> void:
	if not target:
		return

	var target_pos := target.global_position + target_offset
	var desired_rotation := Quaternion.from_euler(Vector3(deg_to_rad(_pitch), _yaw, 0.0))
	var desired_offset := desired_rotation * Vector3(0, 0, _get_collision_distance(target_pos, desired_rotation))

	global_position = global_position.lerp(target_pos + desired_offset, position_smoothing * delta)
	look_at(target_pos)


func _get_collision_distance(origin: Vector3, rotation: Quaternion) -> float:
	var space_state := get_world_3d().direct_space_state
	var ray_dir := rotation * Vector3(0, 0, 1)
	var query := PhysicsRayQueryParameters3D.create(origin, origin + ray_dir * distance, collision_mask)
	query.exclude = [target]
	var result := space_state.intersect_ray(query)

	if result:
		var hit_distance := origin.distance_to(result.position) - collision_margin
		_current_distance = move_toward(_current_distance, hit_distance, 20.0 * get_physics_process_delta_time())
	else:
		_current_distance = move_toward(_current_distance, distance, 5.0 * get_physics_process_delta_time())

	return _current_distance
