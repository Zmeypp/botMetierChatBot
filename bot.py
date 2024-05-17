import discord
import asyncio
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv
import os
import sys
import subprocess

intents = discord.Intents.all()
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)

# Charger les variables d'environnement à partir du fichier .env
load_dotenv()

# Récupérer les informations de connexion à la base de données à partir des variables d'environnement
db_username = os.getenv('DATABASE_USERNAME')
db_password = os.getenv('DATABASE_PASSWORD')
db_host = os.getenv('DATABASE_HOST')
db_name = os.getenv('DATABASE_NAME')
token = os.getenv('TOKEN')

# Configurer la connexion MySQL
config_mysql = {
    'user': db_username,
    'password': db_password,
    'host': db_host,
    'database': db_name
}

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # Vérifie si le message contient uniquement "Bichette" en tant que mot unique
    if "bichette" in message.content.lower() :
        
        def check(m):
            return m.author == message.author and m.channel == message.channel
        
        continue_loop = True
        
        while continue_loop :
            await message.channel.send("Que voulez-vous faire ?\n1. ```Présentation```\n2. ```Ajouter un métier```\n3. ```Maj un métier```\n4. ```Supprimer un métier```\n5. ```Liste de mes métiers```\n6. ```Rechercher un métier```\n7. ```Ne rien faire```")
            message_content = ""
            try:
                connexion_mysql = mysql.connector.connect(**config_mysql)
                print("Connexion SQL établie")
                sys.stdout.flush()
                reply = await client.wait_for('message', check=check, timeout=60)  # Attend une réponse pendant 60 secondes


                if reply.content.lower() == "présentation" or reply.content == "1" :
                    await message.channel.send("Salut Bichette, je suis BichFranceTravail le bot métier de ce serveur tag moi avec 'bichette' si tu veux me parler. J'enregistre les métiers de tous les utilisateurs de ce serveur, comme ça si tu as besoin d'aide sur dofus retro tu sais à qui parler :wink:")
                    continue

                if reply.content.lower() == "ajouter un métier" or reply.content == "2":

                    user_guild_id = message.guild.id
                    choice_metier = True
                    requete_all_metier = "SELECT name FROM possibleMetiers"
                    curseur_all_metier = connexion_mysql.cursor()
                    curseur_all_metier.execute(requete_all_metier)
                    all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                    if all_metiers:
                        # Construire le message avec les métiers disponibles
                        index_metier = {}
                        index = 1
                        for metier in all_metiers:
                            message_content += f"\n{index}. ```{metier}```"
                            index_metier[index] = metier
                            index += 1
                        await message.channel.send(message_content)
                    else:
                        await message.channel.send("Il n'y a aucun métier disponible à ajouter.")

                    
                    try:
                        metier_choice = True
                        while metier_choice == True :
                            message_content = "Quel métier souhaitez-vous ajouter ?"
                            metier_reply = await client.wait_for('message', check=check, timeout=60)
                            choix_utilisateur = metier_reply.content

                            if choix_utilisateur.isdigit() and int(choix_utilisateur) in index_metier :
                                metier = index_metier[int(choix_utilisateur)].capitalize()
                            else :
                                metier = metier_reply.content.capitalize()
                            
                            # Vérifier si le métier est valide en le comparant avec la table possibleMetiers
                            requete_validite_metier = "SELECT COUNT(*) as total FROM possibleMetiers WHERE name = %s"
                            valeurs_validite_metier = (metier,)
                            curseur_validite_metier = connexion_mysql.cursor(dictionary=True)
                            curseur_validite_metier.execute(requete_validite_metier, valeurs_validite_metier)
                            validite_metier_resultat = curseur_validite_metier.fetchone()
                            total_validite_metier = validite_metier_resultat["total"]
                            curseur_validite_metier.close()

                            if not total_validite_metier:
                                await message.channel.send(f"{metier.capitalize()} n'est pas un métier valide. Veuillez choisir parmi les métiers disponibles.")
                            else : 
                                metier_choice = False
                                break
                            
                        lvl_choice = True
                        while lvl_choice==True :
                            await message.channel.send("A quel niveau est le métier ?")
                            lvl_reply = await client.wait_for('message', check=check, timeout=60)
                            lvl = int(lvl_reply.content)
                            
                            if lvl < 1 or lvl > 100:
                                await message.channel.send("Le niveau du métier doit être situé entre 1 et 100.")
                            else :
                                lvl_choice = False
                            
                        
                        user_id = message.author.id

                        # Vérifier si l'utilisateur possède déjà ce métier
                        if is_metier_exist(user_id, metier, user_guild_id, connexion_mysql):
                            # Si oui, demander à l'utilisateur s'il veut mettre à jour le niveau
                            await message.channel.send(f"Vous possédez déjà le métier {metier}. Voulez-vous mettre à jour le niveau ? (oui/non)")
                            try:
                                update_reply = await client.wait_for('message', check=check, timeout=60)
                                if update_reply.content.lower() == "oui":
                                    # Effectuer la mise à jour du métier
                                    maj_metier(user_id, metier, lvl, user_guild_id, connexion_mysql)
                                    await message.channel.send(f"Le niveau du métier {metier} a été mis à jour pour vous.")
                                elif update_reply.content.lower() == "non":
                                    await message.channel.send("Opération annulée.")
                                else:
                                    await message.channel.send("Réponse non valide. Opération annulée.")
                            except asyncio.TimeoutError:
                                await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                                continue_loop = False
                                break
                        else:
                            # Si l'utilisateur ne possède pas déjà ce métier, l'ajouter normalement
                            ajouter_metier(user_id, metier, lvl, user_guild_id, connexion_mysql)
                            await message.channel.send(f"Le métier {metier} de niveau {lvl} a été ajouté pour vous.")
                            

                    except asyncio.TimeoutError:
                        await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                        continue_loop = False
                        break
                    except ValueError:
                        await message.channel.send("Le niveau du métier doit être un nombre entier.")
                        continue_loop = False
                        break

                elif reply.content.lower() == "maj un métier" or reply.content == "3":
                    
                    choice_metier = True
                    while choice_metier == True :
                        user_id = message.author.id
                        user_guild_id = message.guild.id

                        requete_all_metier = f"SELECT metierName FROM metiers WHERE user = {user_id} and guild = {user_guild_id}"
                        curseur_all_metier = connexion_mysql.cursor()
                        curseur_all_metier.execute(requete_all_metier)
                        all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                        if all_metiers:
                            # Construire le message avec les métiers disponibles
                            message_content = "Quel métier souhaitez-vous mettre à jour ?"
                            index_metier = {}
                            index = 1
                            for metier in all_metiers:
                                # Vérifier si le métier est de niveau 100
                                requete_niveau_metier = f"SELECT niveau FROM metiers WHERE metierName = '{metier}' AND user = {user_id} AND guild = {user_guild_id}"
                                curseur_niveau_metier = connexion_mysql.cursor()
                                curseur_niveau_metier.execute(requete_niveau_metier)
                                niveau_metier = curseur_niveau_metier.fetchone()[0]
                                if niveau_metier < 100:
                                    message_content += f"\n{index}. ```{metier}```"
                                    index_metier[index] = metier
                                    index += 1
                                curseur_niveau_metier.close()
                            if index == 1:
                                await message.channel.send("Il n'y a aucun métier disponible à mettre à jour.")
                            else:
                                await message.channel.send(message_content)
                        else:
                            await message.channel.send("Il n'y a aucun métier disponible à mettre à jour.")

                                    
                        try:
                            metier_reply = await client.wait_for('message', check=check, timeout=60)
                            choix_utilisateur = metier_reply.content

                            if choix_utilisateur.isdigit() and int(choix_utilisateur) in index_metier :
                                metier = index_metier[int(choix_utilisateur)].capitalize()
                            else :
                                metier = metier_reply.content.capitalize()
                            
                            # Vérifier si le métier est valide en le comparant avec la table possibleMetiers
                            requete_validite_metier = "SELECT COUNT(*) as total FROM possibleMetiers WHERE name = %s"
                            valeurs_validite_metier = (metier,)
                            curseur_validite_metier = connexion_mysql.cursor(dictionary=True)
                            curseur_validite_metier.execute(requete_validite_metier, valeurs_validite_metier)
                            validite_metier_resultat = curseur_validite_metier.fetchone()
                            total_validite_metier = validite_metier_resultat["total"]
                            curseur_validite_metier.close()

                            if not total_validite_metier:
                                await message.channel.send(f"{metier.capitalize()} n'est pas un métier valide. Veuillez choisir parmi les métiers disponibles.")
                            else :
                                choice_metier = False
                                break


                            
                        except asyncio.TimeoutError:
                            await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                            choice_metier = False
                            continue_loop = False
                            return
                        except ValueError:
                            await message.channel.send("Le niveau du métier doit être un nombre entier.")
                            return

                    
                    try :
                        choice_lvl = True
                        while choice_lvl == True :
                            await message.channel.send("A quel niveau est le métier désormai ?")
                            lvl_reply = await client.wait_for('message', check=check, timeout=60)
                            lvl = int(lvl_reply.content)
                            
                            if lvl < 1 or lvl > 100:
                                await message.channel.send("Le niveau du métier doit être situé entre 1 et 100.")
                                continue
                            
                            user_id = message.author.id
                            

                            maj_metier(user_id, metier, lvl, user_guild_id, connexion_mysql)
                            
                            # Ajoutez ici la logique pour enregistrer le métier avec le niveau dans la base de données
                            await message.channel.send(f"Le métier {metier} de niveau {lvl} a été mis à jour pour vous.")
                            choice_lvl = False
                            break
                        
                    
                    except asyncio.TimeoutError:
                        await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                        continue_loop = False
                        return
                    except ValueError:
                        await message.channel.send("Le niveau du métier doit être un nombre entier.")
                        continue_loop = False
                        return

                
                elif reply.content.lower() == "supprimer un métier" or reply.content == "4":
                    

                    

                    
                    try:
                        
                        user_id = message.author.id
                        user_guild_id = message.guild.id

                        choice_metier = True
                        while choice_metier == True :
                            requete_all_metier = f"SELECT metierName FROM metiers WHERE user = {user_id} and guild = {user_guild_id}"
                            curseur_all_metier = connexion_mysql.cursor()
                            curseur_all_metier.execute(requete_all_metier)
                            all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                            if all_metiers:
                                # Construire le message avec les métiers disponibles
                                message_content = "Quel métier souhaitez-vous supprimer ?"
                                index_metier = {}
                                index = 1
                                for metier in all_metiers:
                                    message_content += f"\n{index}. ```{metier}```"
                                    index_metier[index] = metier
                                    index += 1
                                await message.channel.send(message_content)
                            else:
                                await message.channel.send("Il n'y a aucun métier disponible à supprimer.")
                                choice_metier = False
                                break
                            
                            metier_reply = await client.wait_for('message', check=check, timeout=60)
                            choix_utilisateur = metier_reply.content

                            if choix_utilisateur.isdigit() and int(choix_utilisateur) in index_metier :
                                metier = index_metier[int(choix_utilisateur)].capitalize()
                            else :
                                metier = metier_reply.content.capitalize()
                            
                            # Vérifier si le métier est valide en le comparant avec la table possibleMetiers
                            requete_validite_metier = "SELECT COUNT(*) as total FROM possibleMetiers WHERE name = %s"
                            valeurs_validite_metier = (metier,)
                            curseur_validite_metier = connexion_mysql.cursor(dictionary=True)
                            curseur_validite_metier.execute(requete_validite_metier, valeurs_validite_metier)
                            validite_metier_resultat = curseur_validite_metier.fetchone()
                            total_validite_metier = validite_metier_resultat["total"]
                            curseur_validite_metier.close()

                            if not total_validite_metier:
                                await message.channel.send(f"{metier.capitalize()} n'est pas un métier valide. Veuillez choisir parmi les métiers disponibles.")
                                continue
                            
                            user_id = message.author.id
                            

                            delete_metier(user_id, metier, user_guild_id, connexion_mysql)
                            
                            # Ajoutez ici la logique pour enregistrer le métier avec le niveau dans la base de données
                            await message.channel.send(f"Le métier {metier} a été supprimé pour vous.")
                            choice_metier = False
                            break
                    
                    except asyncio.TimeoutError:
                        await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                    except ValueError:
                        await message.channel.send("Le niveau du métier doit être un nombre entier.")


                elif reply.content.lower() == "liste de mes métiers" or reply.content == "5":
                    user_guild_id = message.guild.id
                    user_id = message.author.id
                    

                    my_metiers = watchme(user_id, user_guild_id, connexion_mysql)

                    try :
                        if my_metiers :
                            metiers_str = "\n".join([f"{metier[0]} (niveau {metier[1]})" for metier in my_metiers])
                            await message.channel.send(f"Vos métiers :\n{metiers_str}")
                        else:
                            await message.channel.send("Vous n'avez pas encore de métier.")

                        
                    
                    except asyncio.TimeoutError:
                        await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                    except ValueError:
                        await message.channel.send("Le niveau du métier doit être un nombre entier.")






                elif reply.content.lower() == "rechercher un métier" or reply.content == "6":
                    user_guild_id = message.guild.id
                    

                    
                    try:

                        choice_metier = True
                        while choice_metier == True :
                            requete_all_metier = "SELECT name FROM possibleMetiers"
                            curseur_all_metier = connexion_mysql.cursor()
                            curseur_all_metier.execute(requete_all_metier)
                            all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                            if all_metiers:
                                # Construire le message avec les métiers disponibles
                                message_content = "Quel métier souhaitez-vous rechercher ?"
                                index_metier = {}
                                index = 1
                                for metier in all_metiers:
                                    message_content += f"\n{index}. ```{metier}```"
                                    index_metier[index] = metier
                                    index += 1
                                await message.channel.send(message_content)
                            else:
                                await message.channel.send("Il n'y a aucun métier disponible à ajouter.")
                                choice_metier = False
                                break

                            metier_reply = await client.wait_for('message', check=check, timeout=60)
                            choix_utilisateur = metier_reply.content

                            if choix_utilisateur.isdigit() and int(choix_utilisateur) in index_metier :
                                metier = index_metier[int(choix_utilisateur)].capitalize()
                            else :
                                metier = metier_reply.content.capitalize()
                            
                            # Vérifier si le métier est valide en le comparant avec la table possibleMetiers
                            requete_validite_metier = "SELECT COUNT(*) as total FROM possibleMetiers WHERE name = %s"
                            valeurs_validite_metier = (metier,)
                            curseur_validite_metier = connexion_mysql.cursor(dictionary=True)
                            curseur_validite_metier.execute(requete_validite_metier, valeurs_validite_metier)
                            validite_metier_resultat = curseur_validite_metier.fetchone()
                            total_validite_metier = validite_metier_resultat["total"]
                            curseur_validite_metier.close()

                            if not total_validite_metier:
                                await message.channel.send(f"{metier.capitalize()} n'est pas un métier valide. Veuillez choisir parmi les métiers disponibles.")
                                continue
                            
                            
                            resultats = search(metier, user_guild_id, connexion_mysql)

                            if resultats :
                                # Organiser les résultats par niveau
                                niveaux_utilisateurs = {}
                                for resultat in resultats:
                                    niveau = resultat['niveau']
                                    utilisateur_id = resultat['user']

                                    user = message.guild.get_member(utilisateur_id)

                                    if user:
                                        utilisateur_nom = user.nick
                                    else:
                                        utilisateur_nom = f"Utilisateur inconnu ({utilisateur_id})"
                                    print(utilisateur_nom)

                                    if niveau not in niveaux_utilisateurs:
                                        niveaux_utilisateurs[niveau] = []
                                    niveaux_utilisateurs[niveau].append(utilisateur_nom)

                                # Créer le message de sortie
                                message_sortie = f"Joueurs ayant le métier '{metier.capitalize()}' et leurs niveaux :\n"

                                for niveau, utilisateurs in niveaux_utilisateurs.items():
                                    utilisateurs_str = "\n    ".join(utilisateurs)
                                    message_sortie += f"\nlvl {str(niveau)} :\n    {utilisateurs_str}"

                                await message.channel.send(message_sortie)

                                

                            else :
                                await message.channel.send("Aucun utilisateur ne possède ce métier.")
                                choice_metier = False
                                break

                    except asyncio.TimeoutError:
                        await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                        continue_loop = False
                        break






                elif reply.content.lower() == "ne rien faire" or reply.content == "7":
                    await message.channel.send("Vous avez choisi de ne rien faire. Votre sentence est irrévocable.")
                    await message.channel.send("https://tenor.com/view/ah-denis-brogniart-denis-brogniart-ah-koh-lanta-gif-24266348")
                    continue_loop = False
                    break

                elif reply.content.lower() == "get logs" :
                    logs = await get_docker_logs('bot', message=message)
                    continue_loop = False
                    break

                
                elif reply.content == "666" :
                    await message.channel.send("Tu as trouvé un easter egg.")
                    await message.channel.send("https://tenor.com/view/devil-twerk-halloween-funny-satan-gif-24351935")

                elif reply.content.lower() == "roll" :
                    await message.channel.send("Un super easter egg !")
                    await message.channel.send('https://cdn.discordapp.com/attachments/664217071151874119/1240714992500736082/3wGT.gif?ex=66483a21&is=6646e8a1&hm=59b6e72a2519bd381e1e1bfb175876f8cd65a01030e6cb3076e5d9f2f1291f6f&')

                else :
                    await message.channel.send("Votre choix n'est pas valide. Veuillez me rappeler avec le mot 'Bichette' lorsque vous saurez quoi faire.")
                    continue_loop = False
                    break
                    
                    
            except asyncio.TimeoutError:
                await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                continue_loop = False
                break
            finally :
                connexion_mysql.close()
                print("Connexion SQL fermée")
                sys.stdout.flush()


def ajouter_metier(user_id, metier_name, niveau, guild, connexion_mysql):
    try:

        # Exécution de la requête SQL pour enregistrer le métier pour l'utilisateur
        requete_enregistrement = "INSERT INTO metiers (user, metierName, niveau, guild) VALUES (%s, %s, %s, %s)"
        valeurs_enregistrement = (user_id, metier_name.capitalize(), niveau, guild)

        curseur_enregistrement = connexion_mysql.cursor(dictionary=True)
        curseur_enregistrement.execute(requete_enregistrement, valeurs_enregistrement)
        connexion_mysql.commit()  # Committer la transaction pour appliquer les changements
        curseur_enregistrement.close()

        print(f"Le métier {metier_name.capitalize()} de niveau {niveau} a été correctement ajouté pour l'utilisateur {user_id}")
        
    except mysql.connector.Error as err:
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        if 'connexion_mysql' in locals() and connexion_mysql.is_connected():
            connexion_mysql.close()

def maj_metier(user_id, metier_name, niveau, guild, connexion_mysql) :
    try :
        requete_maj = "UPDATE metiers SET niveau = %s WHERE user = %s AND metierName = %s AND guild = %s"
        valeur_maj = (niveau, user_id, metier_name.capitalize(), guild)

        curseur_maj = connexion_mysql.cursor(dictionary=True)
        curseur_maj.execute(requete_maj, valeur_maj)
        connexion_mysql.commit()
        curseur_maj.close()

        print(f"Le métier {metier_name.capitalize()} de niveau {niveau} a été correctement mis à jour pour l'utilisateur {user_id}")

    except mysql.connector.Error as err :
        print(f"Erreur de connexion MySQL : {err}")
    finally :
        if 'connexion_mysql' in locals() and connexion_mysql.is_connected() :
            connexion_mysql.close()

def delete_metier(user_id, metier_name, guild, connexion_mysql) :
    try :
        requete_suppression = "DELETE FROM metiers WHERE user = %s AND metierName = %s AND guild = %s"
        valeurs_suppression = (user_id, metier_name.capitalize(), guild)

        curseur_suppression = connexion_mysql.cursor(dictionary=True)
        curseur_suppression.execute(requete_suppression, valeurs_suppression)
        connexion_mysql.commit()  # Committer la transaction pour appliquer les changements
        curseur_suppression.close()

        print(f"Le métier {metier_name.capitalize()} a été correctement supprimé pour l'utilisateur {user_id}")

    except mysql.connector.Error as err :
        print(f"Erreur de connexion MySQL : {err}")
    finally :
        if 'connexion_mysql' in locals() and connexion_mysql.is_connected() :
            connexion_mysql.close()


def watchme(user_id, guild, connexion_mysql) :
    requete_myself = "SELECT metierName, niveau FROM metiers WHERE user = %s AND guild = %s"
    valeur_myself = (user_id, guild,)

    curseur_myself = connexion_mysql.cursor()
    curseur_myself.execute(requete_myself, valeur_myself)
    my_metiers = curseur_myself.fetchall()
    curseur_myself.close()

    return my_metiers


def search(metier_name, guild, connexion_mysql) :
    try :
        requete_search = f'SELECT user, niveau FROM metiers WHERE metierName = "{metier_name.capitalize()}" AND guild = "{guild}" ORDER BY niveau DESC'
        curseur = connexion_mysql.cursor(dictionary=True)
        curseur.execute(requete_search)
        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except mysql.connector.Error as err :
        print(f"Erreur de connexion MySQL : {err}")
    finally :
        if 'connexion_mysql' in locals() and connexion_mysql.is_connected() :
            connexion_mysql.close()

def is_metier_exist(user_id, metier_name, guild, connexion_mysql):
    try:
        requete_metier = "SELECT COUNT(*) as total FROM metiers WHERE user = %s AND metierName = %s AND guild = %s"
        valeurs_metier = (user_id, metier_name.capitalize(), guild)
        
        curseur_metier = connexion_mysql.cursor(dictionary=True)
        curseur_metier.execute(requete_metier, valeurs_metier)
        result = curseur_metier.fetchone()["total"] > 0
        curseur_metier.close()
        
        return result
    except mysql.connector.Error as err:
        print(f"Erreur de connexion MySQL : {err}")
        return False

async def get_docker_logs(container_name, message):
    try:
        # Commande SSH pour se connecter au système hôte et exécuter la commande Docker logs
        ssh_command = f'sshpass -p "Lvnp1parm1rqdev!482" ssh -o StrictHostKeyChecking=no EraserheadMHA@192.168.0.81 "/usr/local/bin/docker logs {container_name} 2>&1"'
        
        # Exécuter la commande SSH et capturer la sortie
        result = subprocess.run(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Vérifier si la commande s'est exécutée avec succès
        if result.returncode == 0:
            # Diviser les logs en morceaux de taille maximale de 1999 caractères
            logs = result.stdout.strip()
            log_chunks = [logs[i:i+1999] for i in range(0, len(logs), 1999)]
            # Envoyer chaque morceau de logs
            for chunk in log_chunks:
                await message.channel.send(chunk)
        else:
            # Retourner l'erreur
            error_message = result.stderr.strip() if result.stderr else "Erreur lors de l'exécution de la commande Docker."
            await message.channel.send(error_message)
    except Exception as e:
        await message.channel.send(f"Une erreur s'est produite: {e}")



client.run(token)