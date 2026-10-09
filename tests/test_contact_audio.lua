local original=love.audio
local plays=0
love.audio={newSource=function(path,kind)
    assert(path=="assets/cue.wav" and kind=="static")
    return {stop=function() end,play=function() plays=plays+1 end}
end}
local audio=require("presentation.contact_audio")
local fact={sound="assets/cue.wav"}
assert(audio.present(fact) and plays==1)
assert(not audio.present(fact) and plays==1,"same contact replayed audio")
assert(not audio.present(nil) and not audio.present({}),"empty contact emitted audio")
assert(audio.present({sound="assets/cue.wav"}) and plays==2,"new contact did not emit")
love.audio=original
package.loaded["presentation.contact_audio"]=nil
print("CONTACT AUDIO TESTS OK")
return true
