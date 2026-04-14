extends Area3D
class_name Interactable

signal on_interact(interactor: Node3D)

@export var hint_text: String = "Press E to interact"
@export var single_use: bool = false

var _used: bool = false


func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)


func interact(interactor: Node3D) -> void:
	if _used:
		return
	on_interact.emit(interactor)
	if single_use:
		_used = true


func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player"):
		body.get_node_or_null("HUD")
		var hud := _find_hud()
		if hud:
			hud.show_interact_hint(hint_text)


func _on_body_exited(body: Node3D) -> void:
	if body.is_in_group("player"):
		var hud := _find_hud()
		if hud:
			hud.hide_interact_hint()


func _find_hud() -> Node:
	var scene_root := get_tree().current_scene
	return scene_root.get_node_or_null("HUD")
