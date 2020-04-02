from zeep import Client
from flask import Flask, request, render_template
import requests, json
from datetime import datetime


TOKEN = "a0a317de-9bd1-4704-8c04-5c968f7c1b7f"
"""navitia playgroud http://doc.navitia.io/
Comment vous authentifier à l'API ?
Accédez à l'API : https://api.sncf.com/v1"""

app = Flask("app")

#Page d'acceuil lors de l'accés à l'application
@app.route('/')
def index():
    return render_template("Accueil.html")

#Fonction principale qui fait tout
@app.route('/Calcul', methods=['GET', 'POST'])
def Calcul():
    if request.method == 'POST':
        result = request.form

        #Bloc pour la partie SOAP. Récupère la latitude et longitude des villes demandé et contact le service SOAP pour calculer la distance en km
        client = Client('http://etrs804-soap.herokuapp.com/services/CalculDistance?wsdl')
        api_ville1= requests.get("https://ressources.data.sncf.com/api/records/1.0/search/?dataset=referentiel-gares-voyageurs&q="+result["villedepart"]).json()
        latitudeA= api_ville1['records'][0]['fields']['wgs_84'][0]
        longitudeA= api_ville1['records'][0]['fields']['wgs_84'][1]
        api_ville2= requests.get("https://ressources.data.sncf.com/api/records/1.0/search/?dataset=referentiel-gares-voyageurs&q="+result["villearrive"]).json()
        latitudeB= api_ville2['records'][0]['fields']['wgs_84'][0]
        longitudeB= api_ville2['records'][0]['fields']['wgs_84'][1]
        d = client.service.calculDistance(latitudeA, latitudeB, longitudeA, longitudeB)
        d = "%.2f" % d

        #Bloc pour la partie RERST. Construction de la requète avec la distance et la devise. Calcul du prix en fonction de la distance et de la devise.
        payload = {'km': d, 'devise': result['devise']}
        p = requests.get('https://etrs804-rest.herokuapp.com/', params=payload).json()
        p = "%.2f" % p['Prix']

        #Récupération des UIC des villes. Les UIC servirons à identifier les villes pour l'intérogation de l'API.
        UIC1 = api_ville1['records'][0]['fields']['pltf_uic_code']
        UIC2 = api_ville2['records'][0]['fields']['pltf_uic_code']
        
        #Formatage de la date et de l'horaire voulu
        horairesvoulu = result["joursdepart"]+" "+result["heuresdepart"]
        dt = datetime.strptime(horairesvoulu, "%Y-%m-%d %H:%M")
        horairesvouluAPIsncf = datetime.strftime(dt, '%Y%m%dT%H%M%S')

        #Construction de la requète vers l'API.
        payload = {'from': 'stop_area:OCE:SA:'+str(UIC1), 'to': 'stop_area:OCE:SA:'+str(UIC2), 'min_nb_journeys': 5, 'datetime': horairesvouluAPIsncf}
        api_get_train = requests.get('https://api.sncf.com/v1/coverage/sncf/journeys?', params=payload, auth=(TOKEN, '')).json()

        #Création des tableau pour la manipulation des informations retourné par l'API.
        tabtrain = []
        tabvraidepart = []

        #Condition en cas d'erreur, ou de recupération de donnée éronné
        if 'error' in api_get_train:
            tabvraidepart.append("Aucun train trouvé ou disponible")
        else:
            n = len(api_get_train['journeys'])
            #Boucle pour récupérer les horaires des prochains trains
            if n > 0:
                for i in range(0, n):
                    tabtrain.append(api_get_train['journeys'][i]['departure_date_time'])
                #Formatage des horaires récupéré.
                u = 0
                for train in tabtrain:
                    u = u+1
                    vraidepart = datetime.strptime(train.replace('T',''),'%Y%m%d%H%M%S')
                    tabvraidepart.append("Train numero "+str(u)+", départ le: "+str(vraidepart))
            else:
                tabvraidepart.append("Aucun train trouvé ou disponible")

        return render_template("Result.html", distance=d, tableau=tabvraidepart, prix=p, devise=result['devise'])

#app.run(debug=True)
