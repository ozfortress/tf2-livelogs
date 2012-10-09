import socket

print "Creating client socket"
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(('192.168.35.128', 61222))
testm = "LIVELOG!123test!192.168.0.4!27015!John"
slen = client.send(testm)

rsp = client.recv(1024)

client.close()

print "Server responded: %s" % rsp

#LIVELOG!123test!192.168.35.128!42276
tokenized = rsp.split('!')

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.connect((tokenized[2], int(tokenized[3])))

client.send('L 10/01/2012 - 21:38:18: "Liquid\'zato<46><STEAM_0:0:42607036><Blue>" say "glhf"')
client.send('L 10/01/2012 - 21:38:22: "[v3] Jak<49><STEAM_0:0:18518582><Red>" say "glhf"')
client.send('L 10/01/2012 - 21:38:26: "Liquid\'Time<41><STEAM_0:1:19238234><Blue>" say "gl hf"')
client.send('L 10/01/2012 - 21:38:27: "[v3] taintedromance<52><STEAM_0:0:41933053><Red>" triggered "healed" against "[v3] Chrome<48><STEAM_0:1:41365809><Red>" (healing "19")')
client.send('L 10/01/2012 - 21:38:29: "Liquid\'Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "healed" against "Liquid\'Shneaky<45><STEAM_0:0:25721066><Blue>" (healing "27")')
client.send('L 10/01/2012 - 21:38:29: "Liquid\'Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "healed" against "Liquid\'Shneaky<45><STEAM_0:0:25721066><Blue>" (healing "2")')
client.send('L 10/01/2012 - 21:38:30: "Liquid\'HerO<43><STEAM_0:1:18855481><Blue>" triggered "damage" (damage "4")')
client.send('L 10/01/2012 - 21:38:30: "[v3] taintedromance<52><STEAM_0:0:41933053><Red>" triggered "healed" against "[v3] Roight<53><STEAM_0:0:8283620><Red>" (healing "26")')
client.send('L 10/01/2012 - 21:38:31: "[v3] Kaki<51><STEAM_0:1:35387674><Red>" triggered "damage" (damage "46")')
client.send('L 10/01/2012 - 21:38:31: "[v3] Kaki<51><STEAM_0:1:35387674><Red>" triggered "damage" (damage "46")')
client.send('L 10/01/2012 - 21:38:31: "Liquid\'ShuZ<42><STEAM_0:0:5269933><Blue>" triggered "damage" (damage "39")')
client.send('L 10/01/2012 - 21:38:31: "[v3] taintedromance<52><STEAM_0:0:41933053><Red>" triggered "healed" against "[v3] Roight<53><STEAM_0:0:8283620><Red>" (healing "14")')
client.send('L 10/01/2012 - 21:38:31: "[v3] Jak<49><STEAM_0:0:18518582><Red>" triggered "damage" (damage "3")')
client.send('L 10/01/2012 - 21:38:31: "[v3] Jak<49><STEAM_0:0:18518582><Red>" triggered "damage" (damage "3")')
client.send('L 10/01/2012 - 21:38:31: "[v3] Jak<49><STEAM_0:0:18518582><Red>" triggered "damage" (damage "7")')
client.send('L 10/01/2012 - 21:38:32: "Liquid\'HerO<43><STEAM_0:1:18855481><Blue>" triggered "damage" (damage "5")')
client.send('L 10/01/2012 - 21:38:32: "Liquid\'HerO<43><STEAM_0:1:18855481><Blue>" triggered "damage" (damage "3")')
client.send('L 10/01/2012 - 21:38:32: "Liquid\'HerO<43><STEAM_0:1:18855481><Blue>" triggered "damage" (damage "9")')
client.send('L 10/01/2012 - 21:38:32: "[v3] Faithless<47><STEAM_0:0:52150090><Red>" triggered "damage" (damage "10")')
client.send('L 10/01/2012 - 21:38:32: "[v3] taintedromance<52><STEAM_0:0:41933053><Red>" triggered "healed" against "[v3] Chrome<48><STEAM_0:1:41365809><Red>" (healing "8")')
client.send('L 10/01/2012 - 21:38:33: "Liquid\'Time<41><STEAM_0:1:19238234><Blue>" triggered "damage" (damage "22")')
client.send('L 10/01/2012 - 21:38:33: "[v3] Kaki<51><STEAM_0:1:35387674><Red>" triggered "damage" (damage "49")')
client.send('L 10/01/2012 - 21:38:33: "Liquid\'zato<46><STEAM_0:0:42607036><Blue>" triggered "damage" (damage "110")')
client.send('L 10/01/2012 - 21:38:33: "[v3] Faithless<47><STEAM_0:0:52150090><Red>" triggered "damage" (damage "19")')
client.send('L 10/01/2012 - 21:38:34: "Liquid\'Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "healed" against "Liquid\'ShuZ<42><STEAM_0:0:5269933><Blue>" (healing "27")')
client.send('L 10/01/2012 - 21:38:34: "Liquid\'Time<41><STEAM_0:1:19238234><Blue>" triggered "damage" (damage "3")')
client.send('L 10/01/2012 - 21:38:34: "[v3] Chrome<48><STEAM_0:1:41365809><Red>" triggered "damage" (damage "53")')
client.send('L 10/01/2012 - 21:38:34: "[v3] Kaki<51><STEAM_0:1:35387674><Red>" triggered "damage" (damage "40")')
client.send('L 10/01/2012 - 21:38:34: "[v3] Jak<49><STEAM_0:0:18518582><Red>" triggered "damage" (damage "20")')
client.send('L 10/01/2012 - 21:38:34: "Liquid\'zato<46><STEAM_0:0:42607036><Blue>" triggered "damage" (damage "65")')

client.close()
