extends CanvasLayer

signal transition_finished()

@onready var _color_rect: ColorRect = $ColorRect
@onready var _animation_player: AnimationPlayer = $AnimationPlayer

var _is_transitioning: bool = false


func _ready() -> void:
	layer = 10
	_color_rect.color = Color.BLACK
	_color_rect.modulate.a = 0.0


func change_scene(path: String, duration: float = 0.5) -> void:
	if _is_transitioning:
		return
	_is_transitioning = true

	await _fade_out(duration)
	get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	await _fade_in(duration)

	_is_transitioning = false
	transition_finished.emit()


func change_scene_with_reset(path: String, duration: float = 0.5) -> void:
	GameManager.reset()
	await change_scene(path, duration)


func _fade_out(duration: float) -> void:
	var tween := create_tween()
	tween.tween_property(_color_rect, "modulate:a", 1.0, duration)
	await tween.finished


func _fade_in(duration: float) -> void:
	var tween := create_tween()
	tween.tween_property(_color_rect, "modulate:a", 0.0, duration)
	await tween.finished
