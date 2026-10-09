import random
import uuid

ROOMS = ["The Foyer", "The Library", "The Secret Study"]

def generate_mansion(player_ids):
    rng = random.SystemRandom()
    puzzles, keys = [], []
    def add(room, title, story, answer, clues, hints, format_hint):
        key = str(rng.randint(1, 9)) if room < 3 else None
        if key: keys.append(key)
        puzzle = {"id": uuid.uuid4().hex, "room": room, "title": title, "story": story,
                  "answer": answer, "clues": {}, "hints": hints, "format": format_hint, "key": key,
                  "revealed": [], "votes": [], "solved": False}
        # Every clue goes to exactly one player; deal across different people within each puzzle.
        offset = len(puzzles) % len(player_ids)
        for i, clue in enumerate(clues):
            pid = player_ids[(i+offset) % len(player_ids)]
            puzzle["clues"].setdefault(pid, []).append(clue)
        puzzles.append(puzzle)

    symbols = ["moon", "owl", "rose", "star"]
    rng.shuffle(symbols)
    mapping = dict(zip(symbols, rng.sample(range(1, 10), 4)))
    answer = ''.join(str(mapping[s]) for s in symbols)
    add(0, "The brass crest", "Four engraved symbols guard a small brass key. Their order and their values live in different scraps of paper.", answer,
        ["A torn ribbon reads, left to right: " + " → ".join(symbols) + ".",
         "The crest's legend: " + "; ".join(f"{s} = {v}" for s,v in mapping.items()) + "."],
        ["One clue gives the order, another gives the digits.", "Replace each symbol in the ribbon with its digit. Enter four digits without spaces."], "Four digits")
    hour, minute = rng.randint(1, 12), rng.choice([5, 10, 15, 20, 25, 35, 40, 45, 50, 55])
    add(0, "The silent clock", "The grandfather clock has stopped. Set the hour and minute hands to the moment described in the housekeeper's notes.", f"{hour:02}:{minute:02}",
        [f"A diary: 'The hour hand rested on {hour} when the last guest left.'", f"A clockmaker's note: 'The minute hand was {minute//5} marks clockwise from twelve. Each mark means five minutes.'"],
        ["Combine the diary's hour with the clockmaker's minute position.", "Multiply the number of marks by five; use HH:MM, padding the hour with a zero."], "HH:MM, e.g. 03:25")
    words = ["candle", "marble", "garden", "silver", "velvet", "raven"]
    rng.shuffle(words)
    index = rng.randint(1, 6)
    add(1, "The indexed shelf", "A hollow book hides a lock that accepts a single word. Find the indexed word in a line from the missing page.", words[index-1],
        ["The page reads: '" + ' '.join(words) + "'.", f"The librarian's index: 'Take word {index}, counting from one.'"],
        ["The page and index must be read together.", f"Count the words from the beginning and enter word {index}."], "One word")
    word, shift = rng.choice(["lantern", "orchard", "compass", "portrait"]), rng.randint(1, 5)
    cipher = ''.join(chr((ord(c)-97+shift)%26+97) for c in word)
    add(1, "The sealed letter", "The estate's last letter is written in a shifted alphabet. Decode its password to release the second library key.", word,
        [f"The letter contains this password: {cipher.upper()}.", f"A cipher wheel: 'To write a secret, shift each letter FORWARD {shift} places. Wrap Z back to A.'"],
        ["Decoding reverses the direction used to write the secret.", f"Move every letter BACK {shift} places in the alphabet. Enter the decoded word."], "One decoded word")
    dials = dict(zip(["amber", "jade", "ivory"], rng.sample(range(1, 10), 3)))
    order = list(dials); rng.shuffle(order)
    add(2, "The three dials", "Three colored dials conceal a mechanism. Their values and the sequence of the mechanism are kept apart.", ''.join(str(dials[c]) for c in order),
        ["The dial labels: " + "; ".join(f"{c} = {v}" for c,v in dials.items()) + ".", "The mechanism turns in this order: " + ' → '.join(order) + "."],
        ["Use the mechanism's order, rather than the order on the label.", "Write each dial's value in the mechanism's color order, as three digits."], "Three digits")
    wiring = dict(zip(["A", "B", "C", "D"], rng.sample(range(1, 10), 4)))
    path = rng.sample(list(wiring), 3)
    add(2, "The copper circuit", "Route power through three circuit nodes. The path and connector numbers are in separate maintenance records.", ''.join(str(wiring[n]) for n in path),
        ["Power must flow: " + ' → '.join(path) + ".", "Connector labels: " + "; ".join(f"{n} = {v}" for n,v in wiring.items()) + "."],
        ["Translate the route's letters into their connector numbers.", "Read the three nodes along the power path and enter their connector numbers in that order."], "Three digits")
    order = rng.sample(list(range(6)), 6)
    add(3, "The last key", "Six numbered key teeth have been recovered. The final door accepts their digits in the order recorded on two halves of its blueprint.", ''.join(keys[i] for i in order),
        ["First half of the blueprint: key teeth " + ', '.join(str(i+1) for i in order[:3]) + ".", "Second half of the blueprint: key teeth " + ', '.join(str(i+1) for i in order[3:]) + "."],
        ["The recovered key list numbers teeth by puzzle, from one to six.", "Read the digits of the recovered teeth in blueprint order: first half, then second half."], "Six digits")
    return puzzles

def normalize_answer(answer):
    return ''.join(answer.lower().strip().split())
