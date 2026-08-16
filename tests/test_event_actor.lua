-- Registered wrapper: keep Event actor characterization intact, exercise the
-- reusable presentation-controller layer above it, then run the player proof.
require("tests.test_event_actor_core")
require("tests.test_animation_controller")
require("tests.test_event_animation_controller")
require("tests.test_event_presentation_policy")
require("tests.test_animation_signal_command")
require("tests.test_player_actor")