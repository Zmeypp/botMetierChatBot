import mysql.connector
import discord
from discord.ext import tasks
from enum import Enum
from dotenv import load_dotenv
import os

load_dotenv()

bot_token = os.getenv("TOKEN")
db_user = os.getenv("DATABASE_USERNAME")
db_pass = os.getenv("DATABASE_PASSWORD")
db_host = os.getenv("DATABASE_HOST")
db_name = os.getenv("DATABASE_NAME")
guild_id = os.getenv("GUILD_ID")

config_mysql = {
    "user": db_user,
    "password": db_pass,
    "host": db_host,
    "database": db_name,
}

def get_emoji_code(metier):
    metier_emojis = {
        'paysan': ':ear_of_rice:',
        'boulanger': ':bread:',
        'bijoutier': ':ring:',
        'bûcheron': ':deciduous_tree:',
        'cordonnier': ':boot:',
        'mineur': ':pick:',
        'tailleur': ':scissors:',
        'chasseur': ':bow_and_arrow:',
        'boucher': ':cut_of_meat:',
        'sculpteur d\'arc': ':archery:',
        'sculpteur de bâton': ':wood:',
        'sculpteur de baguette': ':magic_wand:',
        'pêcheur': ':fishing_pole_and_fish:',
        'poissonnier': ':fish:',
        'forgeur de dague': ':dagger:',
        'forgeur de marteau': ':hammer:',
        'forgeur d\'épée': ':crossed_swords:',
        'forgeur de pelle': ':pick:',
        'forgeur de hache': ':axe:',
        'alchimiste': ':alembic:',
        'forgeur de bouclier': ':shield:',
        'bricoleur': ':wrench:',
        'sculptemage d\'arc': ':dart:',
        'sculptemage de bâton': ':wood:',
        'sculptemage de baguette': ':magic_wand:',
        'joaillomage': ':gem:',
        'cordomage': ':thread:',
        'costumage': ':kimono:',
        'forgemage de dague': ':dagger:',
        'forgemage de marteau': ':hammer:',
        'forgemage d\'épée': ':crossed_swords:',
        'forgemage de pelle': ':pick:',
        'forgemage de hache': ':axe:'
    }

    # Normaliser le nom du métier
    metier = metier.lower().strip()

    # Vérifier si le métier est dans le dictionnaire
    if metier in metier_emojis:
        return metier_emojis[metier]
    else:
        return None

# This will load the permissions the bot has been granted in the previous configuration
intents = discord.Intents.all()
intents.message_content = True

class aclient(discord.Client):
    def __init__(self):
        super().__init__(intents = intents)
        self.synced = False # added to make sure that the command tree will be synced only once
        self.added = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced: #check if slash commands have been synced 
            await tree.sync(guild = discord.Object(guild_id)) #guild specific: you can leave sync() blank to make it global. But it can take up to 24 hours, so test it in a specific guild.
        self.synced = True
        if not self.added:
            self.added = True
        print(f"Say hi to {self.user}!")

    

client = aclient()
tree = discord.app_commands.CommandTree(client)

@tree.command(description='Ajouter un métier', guild=discord.Object(guild_id))
@discord.app_commands.describe(metier="Nom du métier", lvl="Niveau du métier")
async def add(interaction: discord.Interaction, metier: str, lvl: int) :
    
    try : 
        
        # Connexion à la base de données
        connexion_mysql = mysql.connector.connect(**config_mysql)

        #Récupération de l'id de l'utilisateur
        user = interaction.user.id

        # Vérifier si le métier est valide en le comparant avec la table possibleMetiers
        requete_validite_metier = "SELECT COUNT(*) as total FROM possibleMetiers WHERE name = %s"
        valeurs_validite_metier = (metier.capitalize(),)

        curseur_validite_metier = connexion_mysql.cursor(dictionary=True)
        curseur_validite_metier.execute(requete_validite_metier, valeurs_validite_metier)
        validite_metier_resultat = curseur_validite_metier.fetchone()
        total_validite_metier = validite_metier_resultat["total"]
        curseur_validite_metier.close()

        if not total_validite_metier:
            await interaction.response.send_message(f"{metier.capitalize()} n'est pas un métier valide. Veuillez choisir parmi les métiers disponibles.")
        else :
            # Exécution de la requête SQL pour vérifier si le métier existe déjà
            requete_existence = "SELECT COUNT(*) as total FROM metiers WHERE user = %s AND metierName = %s"
            valeurs_existence = (user, metier.capitalize())

            curseur_existence = connexion_mysql.cursor(dictionary=True)
            curseur_existence.execute(requete_existence, valeurs_existence)
            existence_resultat = curseur_existence.fetchone()
            total_existence = existence_resultat["total"]
            curseur_existence.close()

            if total_existence:
                await interaction.response.send_message(f"Vous avez déjà enregistré le métier de {metier.capitalize()}. Utilisez /update {metier.capitalize()} <niveau> pour mettre à jour le niveau.")

            else:
                try :
                    lvl = int(lvl)
                    if lvl < 1 or lvl > 100 :
                        await interaction.response.send_message(f"Ton niveau doit être situé entre 1 et 100.")
                        return
                except ValueError :
                    await interaction.response.send_message(f"Ton niveau doit être un nombre entier.")
                    return
                # Exécution de la requête SQL pour enregistrer le métier pour l'utilisateur
                requete_enregistrement = "INSERT INTO metiers VALUES (%s, %s, %s)"
                valeurs_enregistrement = (user, metier.capitalize(), lvl)

                curseur_enregistrement = connexion_mysql.cursor(dictionary=True)
                curseur_enregistrement.execute(requete_enregistrement, valeurs_enregistrement)
                connexion_mysql.commit()  # Committer la transaction pour appliquer les changements
                curseur_enregistrement.close()

                await interaction.response.send_message(f"Le métier {metier.capitalize()} de niveau {lvl} a été correctement ajouté pour vous, <@{user}>")
        
        
    except mysql.connector.Error as err :
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
        await interaction.response.send_message("Erreur de connexion à la base de données. Veuillez réessayer plus tard.")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        connexion_mysql.close()


def normalize_apostrophe(text):
    # Remplacez différentes formes d'apostrophes par une apostrophe simple
    normalized_text = text.replace('‘', "'").replace('’', "'").replace('`', "'").replace('´', "'")
    return normalized_text


@tree.command(description="Modifier le niveau d'un métier existant", guild=discord.Object(guild_id))
@discord.app_commands.describe(metier="Nom du métier", lvl="Niveau du métier")
async def update(interaction: discord.Interaction, metier: str, lvl: int) :
    try:
        # Connexion à la base de données
        connexion_mysql = mysql.connector.connect(**config_mysql)

        #Récupération de l'id de l'utilisateur
        user = interaction.user.id

        try:
            lvl = int(lvl)
            if lvl < 1 or lvl > 100:
                await interaction.response.send_message("Le niveau de métier doit être compris entre 1 et 100.")
                return
        except ValueError:
            await interaction.response.send_message("Le niveau de métier doit être un nombre entier.")
            return

        # Normaliser le nom du métier
        metier = normalize_apostrophe(metier)

        # Vérifier si le métier existe déjà pour l'utilisateur
        requete_existence = "SELECT COUNT(*) as total FROM metiers WHERE user = %s AND metierName = %s"
        valeurs_existence = (user, metier.capitalize())

        curseur_existence = connexion_mysql.cursor(dictionary=True)
        curseur_existence.execute(requete_existence, valeurs_existence)
        existence_resultat = curseur_existence.fetchone()
        total_existence = existence_resultat["total"]
        curseur_existence.close()

        if total_existence:
            # Le métier existe, mise à jour du niveau
            requete_update = "UPDATE metiers SET niveau = %s WHERE user = %s AND metierName = %s"
            valeurs_update = (lvl, user, metier.capitalize())

            curseur_update = connexion_mysql.cursor(dictionary=True)
            curseur_update.execute(requete_update, valeurs_update)
            connexion_mysql.commit()  # Committer la transaction pour appliquer les changements
            curseur_update.close()

            await interaction.response.send_message(f"Le niveau du métier {metier.capitalize()} a été mis à jour avec succès.")
        else:
            await interaction.response.send_message(f"Vous n'avez pas encore le métier de {metier.capitalize()} enregistré. Vous pouvez l'enregistrer en utilisant la commande : `/addMetier {metier.capitalize()} {lvl}`.")

    except mysql.connector.Error as err:
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
        await interaction.response.send_message("Erreur de connexion à la base de données. Veuillez réessayer plus tard.")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        connexion_mysql.close()


@tree.command(description='Rechercher un métier', guild=discord.Object(guild_id))
@discord.app_commands.describe(metier="Nom du métier")
async def search(interaction: discord.Interaction, metier: str):
    try:
        # Connexion à la base de données
        connexion_mysql = mysql.connector.connect(**config_mysql)
            
        # Normaliser le nom du métier
        metier = normalize_apostrophe(metier)

        # Récupération des utilisateurs avec le métier spécifique, triés par niveau décroissant
        requete_sql = f'SELECT user, niveau FROM metiers WHERE metierName = "{metier.capitalize()}" ORDER BY niveau DESC'
        print(requete_sql)

        curseur = connexion_mysql.cursor(dictionary=True)
        curseur.execute(requete_sql)
        resultats = curseur.fetchall()
        curseur.close()

        if resultats:
            # Organiser les résultats par niveau
            niveaux_utilisateurs = {}
            for resultat in resultats:
                niveau = resultat['niveau']
                utilisateur_id = resultat['user']
                print(utilisateur_id)

                user = interaction.guild.get_member(utilisateur_id)

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

            await interaction.response.send_message(message_sortie)

        else:
            await interaction.response.send_message(f"Aucun joueur trouvé avec le métier '{metier.capitalize()}'.")

    except mysql.connector.Error as err:
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
        await interaction.response.send_message("Erreur de connexion à la base de données. Veuillez réessayer plus tard.")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        connexion_mysql.close()


@tree.command(description='Supprimer un métier', guild=discord.Object(guild_id))
@discord.app_commands.describe(metier="Nom du métier")
async def delete(interaction: discord.Interaction, metier: str):
    try:
        # Connexion à la base de données
        connexion_mysql = mysql.connector.connect(**config_mysql)
        
        #Récupération de l'id de l'utilisateur
        user = interaction.user.id

        # Normaliser le nom du métier
        metier = normalize_apostrophe(metier)

        # Exécution de la requête SQL pour vérifier si le métier existe
        requete_existence = "SELECT COUNT(*) as total FROM metiers WHERE user = %s AND metierName = %s"
        valeurs_existence = (user, metier.capitalize())

        curseur_existence = connexion_mysql.cursor(dictionary=True)
        curseur_existence.execute(requete_existence, valeurs_existence)
        existence_resultat = curseur_existence.fetchone()
        total_existence = existence_resultat["total"]
        curseur_existence.close()

        if total_existence:
            # Exécution de la requête SQL pour supprimer le métier
            requete_suppression = "DELETE FROM metiers WHERE user = %s AND metierName = %s"
            valeurs_suppression = (user, metier.capitalize())

            curseur_suppression = connexion_mysql.cursor(dictionary=True)
            curseur_suppression.execute(requete_suppression, valeurs_suppression)
            connexion_mysql.commit()  # Committer la transaction pour appliquer les changements
            curseur_suppression.close()

            await interaction.response.send_message(f"Le métier de {metier.capitalize()} a été supprimé avec succès.")
        else:
            await interaction.response.send_message(f"Vous n'avez pas enregistré le métier de {metier.capitalize()}.")

    except mysql.connector.Error as err:
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
        await interaction.response.send_message("Erreur de connexion à la base de données. Veuillez réessayer plus tard.")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        connexion_mysql.close()



@tree.command(description='Avoir la liste de tous les métiers existants', guild=discord.Object(guild_id))
@discord.app_commands.describe()
async def list(interaction: discord.Interaction):
    try:
        # Connexion à la base de données
        connexion_mysql = mysql.connector.connect(**config_mysql)

        # Exécution de la requête SQL pour récupérer tous les métiers possibles
        requete_liste_metiers = "SELECT name FROM possibleMetiers"

        curseur_liste_metiers = connexion_mysql.cursor(dictionary=True)
        curseur_liste_metiers.execute(requete_liste_metiers)
        liste_metiers_resultat = curseur_liste_metiers.fetchall()
        curseur_liste_metiers.close()

        if liste_metiers_resultat:
            liste_metiers = [metier["name"] for metier in liste_metiers_resultat]
            await interaction.response.send_message("Liste des métiers possibles :\n" + "\n".join(liste_metiers))
        else:
            await interaction.response.send_message("Aucun métier n'est disponible.")

    except mysql.connector.Error as err:
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
        await interaction.response.send_message("Erreur de connexion à la base de données. Veuillez réessayer plus tard.")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        connexion_mysql.close()



@tree.command(description='Ajouter un métier pour un autre utilisateur', guild=discord.Object(guild_id))
@discord.app_commands.describe(pour="Nom de l'utilisateur pour qui vous souhaitez ajouter un métier", metier="Nom du métier", lvl="Niveau du métier")
async def addfor(interaction: discord.Interaction, pour: str, metier: str, lvl: int):
    try:

        metier = normalize_apostrophe(metier)

        try:
            lvl = int(lvl)
            if lvl < 1 or lvl > 100:
                await interaction.response.send_message("Le niveau de métier doit être compris entre 1 et 100.")
                return
        except ValueError:
            await interaction.response.send_message("Le niveau de métier doit être un nombre entier.")
            return

        # Connexion à la base de données
        connexion_mysql = mysql.connector.connect(**config_mysql)

        # Récupération de l'ID de l'utilisateur Discord mentionné
        pour = interaction.guild.get_member_named(pour).id

        # Vérifier si le métier est valide en le comparant avec la table possibleMetiers
        requete_validite_metier = "SELECT COUNT(*) as total FROM possibleMetiers WHERE name = %s"
        valeurs_validite_metier = (metier.capitalize(),)

        curseur_validite_metier = connexion_mysql.cursor(dictionary=True)
        curseur_validite_metier.execute(requete_validite_metier, valeurs_validite_metier)
        validite_metier_resultat = curseur_validite_metier.fetchone()
        total_validite_metier = validite_metier_resultat["total"]
        curseur_validite_metier.close()

        if not total_validite_metier:
            await interaction.response.send_message(f"{metier.capitalize()} n'est pas un métier valide. Veuillez choisir parmi les métiers disponibles.")
        else:
            # Exécution de la requête SQL pour vérifier si le métier existe déjà
            requete_existence = "SELECT COUNT(*) as total FROM metiers WHERE user = %s AND metierName = %s"
            valeurs_existence = (pour, metier.capitalize())

            curseur_existence = connexion_mysql.cursor(dictionary=True)
            curseur_existence.execute(requete_existence, valeurs_existence)
            existence_resultat = curseur_existence.fetchone()
            total_existence = existence_resultat["total"]
            curseur_existence.close()

            if total_existence:
                pour = interaction.guild.get_member(pour)
                pour_nom = pour.nick
                await interaction.response.send_message(f"{pour_nom} a déjà enregistré le métier de {metier.capitalize()}. Utilisez /update {metier.capitalize()} <niveau> pour mettre à jour le niveau.")
            else:
                # Exécution de la requête SQL pour enregistrer le métier pour l'utilisateur
                requete_enregistrement = "INSERT INTO metiers VALUES (%s, %s, %s)"
                valeurs_enregistrement = (pour, metier.capitalize(), lvl)

                curseur_enregistrement = connexion_mysql.cursor(dictionary=True)
                curseur_enregistrement.execute(requete_enregistrement, valeurs_enregistrement)
                connexion_mysql.commit()  # Committer la transaction pour appliquer les changements
                curseur_enregistrement.close()
                pour = interaction.guild.get_member(pour)
                pour_nom = pour.nick
                await interaction.response.send_message(f"Le métier de {metier.capitalize()} pour {pour_nom} a été enregistré avec succès.")


    except mysql.connector.Error as err:
        # Gérer les erreurs de connexion MySQL
        print(f"Erreur de connexion MySQL : {err}")
        await interaction.response.send_message("Erreur de connexion à la base de données. Veuillez réessayer plus tard.")
    finally:
        # Fermer la connexion à la base de données dans tous les cas
        connexion_mysql.close()


@tree.command(description='Voir tous mes métiers et leurs lvl', guild=discord.Object(guild_id))
@discord.app_commands.describe()
async def watchme(interaction: discord.Interaction):
    connexion_mysql = mysql.connector.connect(**config_mysql)
    user = interaction.user.id

    requete_my_metier = "SELECT metierName, niveau FROM metiers WHERE user = %s"
    valeurs_my_metier = (user,)

    curseur_my_metier = connexion_mysql.cursor()
    curseur_my_metier.execute(requete_my_metier, valeurs_my_metier)
    my_metiers = curseur_my_metier.fetchall()
    curseur_my_metier.close()

    if my_metiers:
        metiers_str = "\n".join([f"{metier[0]} (niveau {metier[1]})" for metier in my_metiers])
        await interaction.response.send_message(f"Vos métiers :\n{metiers_str}")
    else:
        await interaction.response.send_message("Vous n'avez pas encore de métier.")

# add the token of your bot
client.run(bot_token)
# client.run('your-bot-token-here')