"""
 * ----------------------------------------------------------------------------
 * "THE BEER-WARE LICENSE" 
 * As long as you retain this notice you can do whatever you want with this 
 * stuff. If you meet an employee from Windward some day, and you think this
 * stuff is worth it, you can buy them a beer in return. Windward Studios
 * ----------------------------------------------------------------------------
"""

import random as rand
import traceback
import simpleAStar
from framework import sendOrders, playerPowerSend

NAME = "Sunshine Ponies"
SCHOOL = "Purdue"

class MyPlayerBrain(object):
    """The Python AI class.  This class must have the methods setup and gameStatus."""
    def __init__(self, name=NAME):
        self.name = name #The name of the player.
        
        #The player's avatar (looks in the same directory that this module is in).
        #Must be a 32 x 32 PNG file.
        try:
            avatar = open("MyAvatar.png", "rb")
            avatar_str = b''
            for line in avatar:
                avatar_str += line
            avatar = avatar_str
        except IOError:
            avatar = None # avatar is optional
        self.avatar = avatar
    
    def setup(self, gMap, me, allPlayers, companies, passengers, client, stores, powerUpDeck, framework):
        """
        Called at the start of the game; initializes instance variables.

        gMap -- The game map.
        me -- Your Player object.
        allPlayers -- List of all Player objects (including you).
        companies -- The companies on the map.
        passengers -- The passengers that need a lift.
        client -- TcpClient to use to send orders to the server.
        stores -- All the coffee stores.
        powerUpDeck -- The powerups this player has in their hand (may have to wait before playing it).
        powerUpHand -- The powerups this player can draw.
        myPassenger -- The passenger currently in my limo, none to start.
        MAX_TRIPS_BEFORE_REFILL -- The maximum number of trips allowed before a refill is required.
        
        """
        self.framework = framework
        self.gameMap = gMap
        self.players = allPlayers
        self.me = me
        self.companies = companies
        self.passengers = passengers
        self.client = client
        self.stores = stores
        self.powerUpDeck = powerUpDeck
        self.powerUpHand = []
        self.myPassenger = None
        self.MAX_TRIPS_BEFORE_REFILL = 3

        self.pickup = pickup = self.allPickups(me, passengers)

        # get the path from where we are to the dest.

        path = self.calculatePathPlus1(me, pickup[0].lobby.busStop)
        sendOrders(self, "ready", path, pickup)

    def gameStatus(self, status, playerStatus):
        """
        Called to send an update message to this A.I.  We do NOT have to send a response.

        status -- The status message.
        playerStatus -- The player this status is about. THIS MAY NOT BE YOU.
        players -- The status of all players.
        passengers -- The status of all passengers.

        """

        # bugbug - Framework.cs updates the object's in this object's Players,
        # Passengers, and Companies lists. This works fine as long as this app
        # is single threaded. However, if you create worker thread(s) or
        # respond to multiple status messages simultaneously then you need to
        # split these out and synchronize access to the saved list objects.

        try:
            # bugbug - we return if not us because the below code is only for
            # when we need a new path or our limo hits a bus stop. If you want
            # to act on other players arriving at bus stops, you need to
            # remove this. But make sure you use self.me, not playerStatus for
            # the Player you are updating (particularly to determine what tile
            # to start your path from).
            if playerStatus != self.me:
                return

            ptDest = None
            pickup = []
            
            if status == "UPDATE":
                self.maybePlayPowerUp()
                return
            
            self.displayStatus(status, playerStatus)
            
            
            if (status == "PASSENGER_NO_ACTION" or status == "NO_PATH"):
                if self.me.limo.passenger is None:
                    pickup = self.allPickups(self.me, self.passengers)
                    ptDest = pickup[0].lobby.busStop
                else:
                    ptDest = self.me.limo.passenger.destination.busStop
            elif (status == "PASSENGER_DELIVERED" or
                  status == "PASSENGER_ABANDONED"):
                pickup = self.allPickups(self.me, self.passengers)
                ptDest = pickup[0].lobby.busStop
            elif  status == "PASSENGER_REFUSED_ENEMY":
                ptDest = rand.choice(filter(lambda c: c != self.me.limo.passenger.destination,
                    self.companies)).busStop
            elif (status == "PASSENGER_DELIVERED_AND_PICKED_UP" or
                  status == "PASSENGER_PICKED_UP"):
                pickup = self.allPickups(self.me, self.passengers)
                ptDest = self.me.limo.passenger.destination.busStop
                
            # coffee store override
            """
            if(status == "PASSENGER_DELIVERED_AND_PICKED_UP" or status == "PASSENGER_DELIVERED" or status == "PASSENGER_ABANDONED"):
                if(self.me.limo.coffeeServings <= 0):
                    #ptDest = rand.choice(self.stores).busStop #wat... goes to random coffee place
                    ptDest = self.closestStore(self.me, self.stores).busStop
            elif(status == "PASSENGER_REFUSED_NO_COFFEE" or status == "PASSENGER_DELIVERED_AND_PICK_UP_REFUSED"):
                ptDest = self.closestStore(self.me, self.stores).busStop
            """

            #get coffee if we're ever out and don't have a passenger, or if close to a coffee store anyway, pick up
            if (self.me.limo.coffeeServings <= 0 and
                self.me.limo.passenger is None
                or (self.me.limo.coffeServings == 1 and
                    self.me.limo.passenger is None and
                    self.closestStoreCost(self.me, self.stores).busStop <= 10)) :
                print "looking for coffee"
                ptDest = self.closestStore(self.me, self.stores).busStop

            if(status == "COFFEE_STORE_CAR_RESTOCKED"):
                pickup = self.allPickups(self.me, self.passengers)
                if len(pickup) != 0:
                    ptDest = pickup[0].lobby.busStop
            
            if(ptDest == None):
                return
            
            self.displayOrders(ptDest)
            
            # get the path from where we are to the dest.
            path = self.calculatePathPlus1(self.me, ptDest)

            sendOrders(self, "move", path, pickup)
        except Exception as e:
            print traceback.format_exc()
            raise e

    def displayOrders(self, ptDest):
        msg = None
        potentialStores = [s for s in self.stores if s.busStop == ptDest]
        store = None
        if len(potentialStores) > 0:
            store = potentialStores[0]
        if store is not None:
            storename = store.name
            if "Gloria Jean" in storename:
                storename = "Gloria Jean's Coffees"
            if "Peet" in storename:
                storename = "Peet's Coffee and Tea"
            if "Tully" in storename:
                storename = "Tully's Coffee"
            msg = "Heading toward {0} at {1}".format(storename, ptDest)
        else:
            potentialCompanies = [c for c in self.companies if c.busStop == ptDest]
            company = None
            if len(potentialCompanies) > 0:
                company = potentialCompanies[0]
            if company is not None:
                msg = "Heading toward {0} at {1}".format(company.name, ptDest)
        if msg is not None:
            print(msg)

    def calculatePathPlus1 (self, me, ptDest):
        path = simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, ptDest)
        # add in leaving the bus stop so it has orders while we get the message
        # saying it got there and are deciding what to do next.
        if len(path) > 1:
            path.append(path[-2])
        return path
    
    def maybePlayPowerUp(self):

        # not enough, draw
        if len(self.powerUpHand) < self.me.maxCardsInHand and len(self.powerUpDeck) > 0:
            for card in self.powerUpDeck:
                if(len(self.powerUpHand) == self.me.maxCardsInHand):
                    break
                # select a card
                self.powerUpDeck.remove(card)
                self.powerUpHand.append(card)
                playerPowerSend(self, "DRAW", card)
            return
        
        # can we play one?
        okToPlayHand = filter(lambda p: p.okToPlay, self.powerUpHand)
        if len(okToPlayHand) == 0:
            return
        powerUp = okToPlayHand[0]

        if (powerUp.card == "MULT_DELIVERY_QUARTER_SPEED"):
            playerPowerSend(self, "DISCARD", powerUp)
            return
        
        if (powerUp.card == "MULT_DELIVERING_PASSENGER" or
            powerUp.card == "MULT_DELIVER_AT_COMPANY" or
            powerUp.card == "MULT_DELIVERY_QUARTER_SPEED"):
            # we need extra coffee for these
            # don't play if we don't have enough coffee
            if self.me.limo.coffeeServings <= 1:
                return

        if powerUp.card == "MULT_DELIVER_AT_COMPANY":
            # if we're already going to the destination, play this card
            if powerUp.company == self.me.limo.passenger.destination.name:
                playerPowerSend(self, "PLAY", powerUp)
            return

        if powerUp.card == "MOVE_PASSENGER":
            powerUp.passenger = rand.choice(filter(lambda p: p.car is None, self.passengers))
            playerPowerSend(self, "PLAY", powerUp)
            return

        if powerUp.card == "CHANGE_DESTINATION":
            # highest score player with a passenger in the car plus points delivered if they deliver the passenger they have
            playersWithPassengers = filter(lambda p: p.guid != self.me.guid and p.limo.passenger is not None, self.players)
            playersWithPassengers = sorted(playersWithPassengers, key=lambda x: x.score + x.limo.passenger.pointsDelivered, reverse=True)
            if len(playersWithPassengers) == 0:
                return
            powerUp.player = playersWithPassengers[0]
            playerPowerSend(self, "PLAY", powerUp)
            return

        if powerUp.card == "STOP_CAR":
            # highest score player with or w/o passenger plus points delivered if they deliver the passenger they have
            playersWithPassengers = filter(lambda p: p.guid != self.me.guid, self.players)
            playersWithPassengers = sorted(playersWithPassengers, key=lambda x: x.score + x.limo.passenger.pointsDelivered if x.limo.passenger is not None else x.score, reverse=True)
            if len(playersWithPassengers) == 0:
                return
            powerUp.player = playersWithPassengers[0]
            playerPowerSend(self, "PLAY", powerUp)
            return


        #if we get here, just play the card
        playerPowerSend(self, "PLAY", powerUp)

        print "Playing powerup " + powerUp.card
        self.powerUpHand.remove(powerUp)
        
        return
    
    # A power-up was played. It may be an error message, or success.
    def powerUpStatus(self, status, playerPowerUp, cardPlayed):
        # redo the path if we got relocated
        if((status == "POWER_UP_PLAYED") and ((cardPlayed.card == "RELOCATE_ALL_CARS") or ((cardPlayed.card == "CHANGE_DESTINATION") and (cardPlayed.player.guid == self.me.guid)))):
            self.gameStatus("NO_PATH", self.me)
        return
    
    def displayStatus(self, status, plyrStatus):
        msg = ""
        # Sometimes, myPassenger or myPassenger.lobby is None. If you want to figure this
        # out on your own, have at it, but it really only affects the messages displayed below.
        if(status == "PASSENGER_DELIVERED"):
            if self.myPassenger.name is not None or self.myPassenger.lobby is not None:
                msg = "{0} delivered to {1}\n".format(self.myPassenger.name, self.myPassenger.lobby.name)
            self.myPassenger = None
        elif(status == "PASSENGER_ABANDONED"):
            if self.myPassenger is not None or self.myPassenger.lobby is not None:
                msg = "{0} abandoned at {1}\n".format(self.myPassenger.name, self.myPassenger.lobby.name)
            self.myPassenger = None
        elif(status == "PASSENGER_REFUSED_ENEMY"):
            msg = "{0} refused to exit at {1} - enemy there".format(plyrStatus.limo.passenger.name, plyrStatus.limo.passenger.destination.name)
        elif(status == "PASSENGER_DELIVERED_AND_PICKED_UP"):
            msg = "{0} delivered at {1} and {2} picked up".format(self.myPassenger.name, self.myPassenger.lobby.name, plyrStatus.limo.passenger.name)
            self.myPassenger = plyrStatus.limo.passenger
        elif(status == "PASSENGER_PICKED_UP"):
            msg = "{0} picked up".format(plyrStatus.limo.passenger.name)
            self.myPassenger = plyrStatus.limo.passenger
        elif(status == "PASSENGER_REFUSED_NO_COFFEE"):
            msg = "Passenger refused to board limo, no coffee"
        elif(status == "PASSENGER_DELIVERED_AND_PICK_UP_REFUSED"):
            msg = "{0} delivered at {1}, new passenger refused to board limo, no coffee".format(self.myPassenger.name, self.myPassenger.lobby.name)
        elif(status == "COFFEE_STORE_CAR_RESTOCKED"):
            msg = "Coffee restocked!"
        
        if(msg != ""):
            print (msg)
        return
    
    def allPickups (self, me, passengers):
            pickup = [p for p in passengers if (not p in me.passengersDelivered and
                                                p != me.limo.passenger and
                                                p.car is None and
                                                p.lobby is not None and p.destination is not None)]
            passengerCosts=[]
            for passenger in pickup:
                distToPassenger=len(simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, passenger.lobby.busStop))
                distToDest=len(simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, passenger.destination.busStop))
                cost=( distToPassenger + distToDest) / passenger.pointsDelivered
                passengerCosts.append((passenger,cost))

            # sort & print
            passengerCosts=sorted(passengerCosts,key=lambda x:x[1])
            print passengerCosts

            # returns passenger object
            return [p[0] for p in passengerCosts]

    def allPickupCosts (self, me, passengers):
            pickup = [p for p in passengers if (not p in me.passengersDelivered and
                                                p != me.limo.passenger and
                                                p.car is None and
                                                p.lobby is not None and p.destination is not None)]
            passengerCosts=[]
            for passenger in pickup:
                distToPassenger=len(simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, passenger.lobby.busStop))
                distToDest=len(simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, passenger.destination.busStop))
                cost=( distToPassenger + distToDest) / passenger.pointsDelivered
                passengerCosts.append((passenger,cost))


            # eliminate passengers someone else will get first
            for i,passenger in enumerate(pickup):
                for player in self.players:
                    if(passenger in player.pickup[0]):
                        if(len(player.limo.path)<(len(me.limo.path)-2)):
                            del pickup[i]


            # sort
            passengerCosts=sorted(passengerCosts,key=lambda x:x[1])


            # returns cost
            return [p[1] for p in passengerCosts]

    def closestStore(self, me, stores):
        storeCosts=[]
        for store in stores:
            distToStore=len(simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, store.busStop))
            distToNextPickup = self.allPickupCosts(me, self.passengers)[1]
            cost = distToStore + distToNextPickup
            storeCosts.append((store,cost))

        # sort
        storeCosts = sorted(storeCosts, key=lambda x:x[1])

        return storeCosts[0][0]

    def closestStoreCost(self, me, stores):
        storeCosts=[]
        for store in stores:
            distToStore=len(simpleAStar.calculatePath(self.gameMap, me.limo.tilePosition, store.busStop))
            distToNextPickup = self.allPickupCosts(me, self.passengers)[1]
            cost = distToStore + distToNextPickup
            storeCosts.append((store,cost))

        # sort
        storeCosts = sorted(storeCosts, key=lambda x:x[1])

        return storeCosts[0][1]
