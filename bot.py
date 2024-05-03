import discord
import asyncio
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv
import os

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
connexion_mysql = mysql.connector.connect(**config_mysql)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # Vérifie si le message contient uniquement "Bichette" en tant que mot unique
    if len(message.content.split()) == 1 and message.content.lower() == "bichette" :
        await message.channel.send("Que voulez-vous faire ?\n1. ```Ajouter un métier```\n2. ```Maj un métier```\n3. ```Supprimer un métier```\n4. ```Liste de mes métiers```\n5. ```Rechercher un métier```")
        
        def check(m):
            return m.author == message.author and m.channel == message.channel
        
        try:
            reply = await client.wait_for('message', check=check, timeout=60)  # Attend une réponse pendant 60 secondes
            if reply.content.lower() == "ajouter un métier" or reply.content == "1":
                user_guild_id = message.guild.id
                
                requete_all_metier = "SELECT name FROM possibleMetiers"
                curseur_all_metier = connexion_mysql.cursor()
                curseur_all_metier.execute(requete_all_metier)
                all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                if all_metiers:
                    # Construire le message avec les métiers disponibles
                    message_content = "Quel métier souhaitez-vous ajouter ?"
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
                        return
                    
                    await message.channel.send("A quel niveau est le métier ?")
                    lvl_reply = await client.wait_for('message', check=check, timeout=60)
                    lvl = int(lvl_reply.content)
                    
                    if lvl < 1 or lvl > 100:
                        await message.channel.send("Le niveau du métier doit être situé entre 1 et 100.")
                        return
                    
                    user_id = message.author.id

                    # Vérifier si l'utilisateur possède déjà ce métier
                    if is_metier_exist(user_id, metier, user_guild_id):
                        # Si oui, demander à l'utilisateur s'il veut mettre à jour le niveau
                        await message.channel.send(f"Vous possédez déjà le métier {metier}. Voulez-vous mettre à jour le niveau ? (oui/non)")
                        try:
                            update_reply = await client.wait_for('message', check=check, timeout=60)
                            if update_reply.content.lower() == "oui":
                                # Effectuer la mise à jour du métier
                                maj_metier(user_id, metier, lvl, user_guild_id)
                                await message.channel.send(f"Le niveau du métier {metier} a été mis à jour pour vous.")
                                return
                            elif update_reply.content.lower() == "non":
                                await message.channel.send("Opération annulée.")
                                return
                            else:
                                await message.channel.send("Réponse non valide. Opération annulée.")
                                return
                        except asyncio.TimeoutError:
                            await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                            return
                    else:
                        # Si l'utilisateur ne possède pas déjà ce métier, l'ajouter normalement
                        ajouter_metier(user_id, metier, lvl, user_guild_id)
                        await message.channel.send(f"Le métier {metier} de niveau {lvl} a été ajouté pour vous.")
                        return

                except asyncio.TimeoutError:
                    await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                except ValueError:
                    await message.channel.send("Le niveau du métier doit être un nombre entier.")

            elif reply.content.lower() == "maj un métier" or reply.content == "2":
                
                user_id = message.author.id
                user_guild_id = message.guild.id

                requete_all_metier = f"SELECT metierName FROM metiers WHERE user = {user_id} and guild = {user_guild_id}"
                curseur_all_metier = connexion_mysql.cursor()
                curseur_all_metier.execute(requete_all_metier)
                all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                if all_metiers:
                    # Construire le message avec les métiers disponibles
                    message_content = "Quel métier souhaitez-vous mettre à jour ?"
                    for metier in all_metiers:
                        message_content += f"```{metier}```"
                    await message.channel.send(message_content)
                else:
                    await message.channel.send("Il n'y a aucun métier disponible à mettre à jour.")

                
                try:
                    metier_reply = await client.wait_for('message', check=check, timeout=60)
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
                        return
                    
                    await message.channel.send("A quel niveau est le métier désormai ?")
                    lvl_reply = await client.wait_for('message', check=check, timeout=60)
                    lvl = int(lvl_reply.content)
                    
                    if lvl < 1 or lvl > 100:
                        await message.channel.send("Le niveau du métier doit être situé entre 1 et 100.")
                        return
                    
                    user_id = message.author.id
                    

                    maj_metier(user_id, metier, lvl, user_guild_id)
                    
                    # Ajoutez ici la logique pour enregistrer le métier avec le niveau dans la base de données
                    await message.channel.send(f"Le métier {metier} de niveau {lvl} a été mis à jour pour vous.")
                    return
                
                except asyncio.TimeoutError:
                    await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                except ValueError:
                    await message.channel.send("Le niveau du métier doit être un nombre entier.")
            
            elif reply.content.lower() == "supprimer un métier" or reply.content == "3":
                
                user_id = message.author.id
                user_guild_id = message.guild.id

                requete_all_metier = f"SELECT metierName FROM metiers WHERE user = {user_id} and guild = {user_guild_id}"
                curseur_all_metier = connexion_mysql.cursor()
                curseur_all_metier.execute(requete_all_metier)
                all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                if all_metiers:
                    # Construire le message avec les métiers disponibles
                    message_content = "Quel métier souhaitez-vous supprimer ?"
                    for metier in all_metiers:
                        message_content += f"```{metier}```"
                    await message.channel.send(message_content)
                else:
                    await message.channel.send("Il n'y a aucun métier disponible à supprimer.")
                    return

                
                try:
                    metier_reply = await client.wait_for('message', check=check, timeout=60)
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
                        return
                    
                    user_id = message.author.id
                    

                    delete_metier(user_id, metier, user_guild_id)
                    
                    # Ajoutez ici la logique pour enregistrer le métier avec le niveau dans la base de données
                    await message.channel.send(f"Le métier {metier} a été supprimé pour vous.")
                    return
                
                except asyncio.TimeoutError:
                    await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                except ValueError:
                    await message.channel.send("Le niveau du métier doit être un nombre entier.")

            elif reply.content.lower() == "liste de mes métiers" or reply.content == "4":
                user_guild_id = message.guild.id
                user_id = message.author.id
                

                my_metiers = watchme(user_id, user_guild_id)

                try :
                    if my_metiers :
                        metiers_str = "\n".join([f"{metier[0]} (niveau {metier[1]})" for metier in my_metiers])
                        await message.channel.send(f"Vos métiers :\n{metiers_str}")
                    else:
                        await message.channel.send("Vous n'avez pas encore de métier.")

                    return
                
                except asyncio.TimeoutError:
                    await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")
                except ValueError:
                    await message.channel.send("Le niveau du métier doit être un nombre entier.")

            elif reply.content.lower() == "rechercher un métier" or reply.content == "5":
                user_guild_id = message.guild.id
                requete_all_metier = "SELECT name FROM possibleMetiers"
                curseur_all_metier = connexion_mysql.cursor()
                curseur_all_metier.execute(requete_all_metier)
                all_metiers = [row[0] for row in curseur_all_metier.fetchall()]
                if all_metiers:
                    # Construire le message avec les métiers disponibles
                    message_content = "Quel métier souhaitez-vous ajouter ?"
                    for metier in all_metiers:
                        message_content += f"```{metier}```"
                    await message.channel.send(message_content)
                else:
                    await message.channel.send("Il n'y a aucun métier disponible à ajouter.")

                
                try:
                    metier_reply = await client.wait_for('message', check=check, timeout=60)
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
                        return
                    
                    
                    resultats = search(metier, user_guild_id)

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

                            if niveau not in niveaux_utilisateurs:
                                niveaux_utilisateurs[niveau] = []
                            niveaux_utilisateurs[niveau].append(utilisateur_nom)

                        # Créer le message de sortie
                        message_sortie = f"Joueurs ayant le métier '{metier.capitalize()}' et leurs niveaux :\n"

                        for niveau, utilisateurs in niveaux_utilisateurs.items():
                            utilisateurs_str = "\n    ".join(utilisateurs)
                            message_sortie += f"\nlvl {str(niveau)} :\n    {utilisateurs_str}"

                        await message.channel.send(message_sortie)

                        return

                    else :
                        await message.channel.send("Aucun utilisateur ne possède ce métier.")

                except asyncio.TimeoutError:
                    await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")

            else :
                await message.channel.send("Votre choix n'est pas valide. Veuillez me rappeler avec le mot 'Bichette' lorsque vous saurez quoi faire.")
                
                
        except asyncio.TimeoutError:
            await message.channel.send("Vous avez mis trop de temps à répondre. Opération annulée.")


def ajouter_metier(user_id, metier_name, niveau, guild):
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

def maj_metier(user_id, metier_name, niveau, guild) :
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

def delete_metier(user_id, metier_name, guild) :
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


def watchme(user_id, guild) :
    requete_myself = "SELECT metierName, niveau FROM metiers WHERE user = %s AND guild = %s"
    valeur_myself = (user_id, guild,)

    curseur_myself = connexion_mysql.cursor()
    curseur_myself.execute(requete_myself, valeur_myself)
    my_metiers = curseur_myself.fetchall()
    curseur_myself.close()

    return my_metiers


def search(metier_name, guild) :
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

def is_metier_exist(user_id, metier_name, guild):
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




client.run(token)