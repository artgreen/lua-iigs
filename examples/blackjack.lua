-- Function to shuffle the deck of cards
local function shuffleDeck()
    local suits = { "Hearts", "Diamonds", "Clubs", "Spades" }
    local values = { "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace" }

    local deck = {}
    for _, suit in ipairs(suits) do
        for _, value in ipairs(values) do
            table.insert(deck, value .. " of " .. suit)
        end
    end

    -- Shuffle the deck
    for i = #deck, 2, -1 do
        local j = math.random(i)
        deck[i], deck[j] = deck[j], deck[i]
    end

    return deck
end

-- Function to calculate the total value of a hand
local function calculateHandValue(hand)
    local value = 0
    local hasAce = false

    for _, card in ipairs(hand) do
        local cardValue = tonumber(card:match("%d+")) or (card:match("Ace") and 11) or 10
        value = value + cardValue

        if cardValue == 11 then
            hasAce = true
        end
    end

    -- If the hand value is over 21 and we have an Ace, treat the Ace as 1 instead of 11
    if value > 21 and hasAce then
        value = value - 10
    end

    return value
end

-- Function to draw a card from the deck
local function drawCard(deck, hand)
    local card = table.remove(deck, 1)
    table.insert(hand, card)
end

-- Function to check if the player wants to play again
local function playAgain()
    print("Do you want to play again? (y/n)")
    local input = io.read():lower()
    return input == "y"
end

-- Main game loop
local function main()
    math.randomseed(os.time())
    local playerMoney = 1000

    while true do
        print("Welcome to Blackjack!")
        print("You currently have $" .. playerMoney)

        local deck = shuffleDeck()
        local playerHand = {}
        local dealerHand = {}

        drawCard(deck, playerHand)
        drawCard(deck, dealerHand)
        drawCard(deck, playerHand)

        while true do
            print("Your hand: " .. table.concat(playerHand, ", "))
            print("Dealer's face-up card: " .. dealerHand[1])
            print("Your hand value: " .. calculateHandValue(playerHand))
            print("Options: (h)it, (s)tand")

            local input = io.read():lower()

            if input == "h" then
                drawCard(deck, playerHand)

                if calculateHandValue(playerHand) > 21 then
                    print("Bust! Your hand value is over 21.")
                    break
                end
            elseif input == "s" then
                break
            else
                print("Invalid input. Please try again.")
            end
        end

        -- Dealer's turn
        while calculateHandValue(dealerHand) < 17 do
            drawCard(deck, dealerHand)
        end

        -- Determine the winner
        local playerValue = calculateHandValue(playerHand)
        local dealerValue = calculateHandValue(dealerHand)

        print("Your hand: " .. table.concat(playerHand, ", "))
        print("Your hand value: " .. playerValue)
        print("Dealer's hand: " .. table.concat(dealerHand, ", "))
        print("Dealer's hand value: " .. dealerValue)

        if playerValue > 21 or (dealerValue <= 21 and dealerValue > playerValue) then
            print("Dealer wins!")
            playerMoney = playerMoney - 10
        else
            print("You win!")
            playerMoney = playerMoney + 10
        end

        -- Check if the player wants to play again
        if playerMoney <= 0 then
            print("You've run out of money!")
            break
        elseif not playAgain() then
            break
        end
    end

    print("Thanks for playing Blackjack!")
end

-- Run the game
main()
