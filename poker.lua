-- Define the ranks and suits of a deck of cards
ranks = { "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A" }
suits = { "hearts", "diamonds", "clubs", "spades" }

-- Define a function that checks if a hand contains a flush
function has_flush(hand)
    local suit = nil
    for i, card in ipairs(hand) do
        if suit == nil then
            suit = card.suit
        elseif suit ~= card.suit then
            return false
        end
    end
    return true
end

-- Define a function that checks if a hand contains a straight
function has_straight(hand)
    -- First, sort the hand by rank
    table.sort(hand, function(a, b) return a.rank < b.rank end)

    -- Check for an ace-low straight
    if hand[1].rank == "2" and hand[2].rank == "3" and hand[3].rank == "4" and hand[4].rank == "5" and hand[5].rank == "A" then
        return true
    end

    -- Check for a regular straight
    local rank_index = {}
    for i, rank in ipairs(ranks) do
        rank_index[rank] = i
    end
    for i = 1, #hand - 1 do
        if rank_index[hand[i+1].rank] - rank_index[hand[i].rank] ~= 1 then
            return false
        end
    end

    return true
end

-- Define a function that prints a poker hand
function print_hand(hand)
    for i, card in ipairs(hand) do
        print(card.rank .. " of " .. card.suit)
    end
end

-- Define a function that evaluates a poker hand
function evaluate(hand)
    -- First, count the occurrences of each rank and suit
    count = {}
    suit_count = {}
    for i, card in ipairs(hand) do
        if not count[card.rank] then
            count[card.rank] = 1
        else
            count[card.rank] = count[card.rank] + 1
        end
        if not suit_count[card.suit] then
            suit_count[card.suit] = 1
        else
            suit_count[card.suit] = suit_count[card.suit] + 1
        end
    end

    -- Then, check for different poker hands in descending order of strength
    if suit_count[hand[1].suit] == 5 and has_straight(hand) then
        return "straight flush"
    else
        for _, rank in ipairs(ranks) do
            if count[rank] == 4 then
                return "four of a kind"
            end
        end
    end

    for _, rank in ipairs(ranks) do
        if count[rank] == 3 then
            for _, other_rank in ipairs(ranks) do
                if other_rank ~= rank and count[other_rank] == 2 then
                    return "full house"
                end
            end
            return "three of a kind"
        end
    end

    if suit_count[hand[1].suit] == 5 then
        return "flush"
    end

    if has_straight(hand) then
        return "straight"
    end

    for _, rank in ipairs(ranks) do
        if count[rank] == 2 then
            for _, other_rank in ipairs(ranks) do
                if other_rank ~= rank and count[other_rank] == 2 then
                    return "two pair"
                end
            end
            return "pair"
        end
    end

    return "high card"
end


-- Example usage
local hand = {
    { rank = "K", suit = "hearts" },
    { rank = "K", suit = "diamonds" },
    { rank = "4", suit = "hearts" },
    { rank = "5", suit = "clubs" },
    { rank = "3", suit = "spades" }
}
print_hand(hand)
print(evaluate(hand)) -- Outputs "straight flush"
