from Cryptodome.PublicKey import ECC, DSA

def create_dsa_key_pair(name):
  privkey = "%s.priv"%name
  pubkey = "%s.pub"%name
  
  key = DSA.generate(2048)
  with open(privkey, "w") as fp:
    fp.write(key.export_key("PEM").decode())
  
  with open(pubkey, "w") as fp:
    fp.write(key.publickey().export_key("PEM").decode())

def create_ed25519_key_pair(name):
  pass

def create_key_pair(name, keytype):
  if keytype == "DSA":
    create_dsa_key_pair(name)
  elif keytype == "ED25519":
    create_ed25519_key_pair(name)
  else:
    raise Exception("NOT SUPPORTED")


if __name__=="__main__":
  create_key_pair("dsa_example", "DSA")
  

#>>> from Crypto.PublicKey import ECC
#>>>
#>>> key = ECC.generate(curve='P-256')
#>>>
#>>> f = open('myprivatekey.pem','wt')
#>>> f.write(key.export_key('PEM'))
#>>> f.close()
#...
#>>> f = open('myprivatekey.pem','rt')
#>>> key = RSA.import_key(f.read())

#if __name__=="__main__":
#
