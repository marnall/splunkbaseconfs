# Question sets for the `jev` search command. One stanza per question: [<set>/<question>].
# Stanzas without a slash are ignored.

[<set>/<question>]
type = choice | score | noul
* choice: one of the option.* keys. score: a position on the level.* scale. noul: the probability that the statement is true.
instructions = <string>
* The judgment to make. Reference state fields with backticks, e.g. `examples`.
option.<name> = <string>
* choice only. One key per option, 2 to 255 of them; the value describes it. Include an "other" option.
level.<n> = <string>
* score only. Levels from 0 upwards, 2 to 10 of them, each described as a concrete situation.
label.<n> = <string>
* score only. Short display name for level n, returned as jev_<question>_label. Never sent to the model.
true = <string>
false = <string>
* noul only, optional. What counts as yes and as no.
