local M = {}

local state = {
    selfName = "",
    party = nil,
    invites = {},
    sharedVehicles = {
        own = {},
        borrowed = {},
        ownCount = 0,
        borrowedCount = 0,
        partyTotal = 0,
    },
    marketplace = {
        myListings = {},
        publicListings = {},
        listingCount = 0,
    },
    loaners = {
        given = {},
        received = {},
        givenCount = 0,
        receivedCount = 0,
        total = 0,
    },
}

local syncedOnce = false
local layoutRefreshRequested = false
local processedMarketTransactions = {}
local reconcileLoanerVehicles

local defaultAppLayoutDirectory = "settings/ui_apps/originalLayouts/default/"
local missionAppLayoutDirectory = "settings/ui_apps/originalLayouts/mission/"
local userDefaultAppLayoutDirectory = "settings/ui_apps/layouts/default/"
local userMissionAppLayoutDirectory = "settings/ui_apps/layouts/mission/"

local defaultLayouts = {
    career = { filename = "career" },
    careerBigMap = { filename = "careerBigMap" },
    careerMission = { filename = "careerMission" },
    careerMissionEnd = { filename = "careerMissionEnd" },
    careerPause = { filename = "careerPause" },
    careerRefuel = { filename = "careerRefuel" },
    freeroam = { filename = "freeroam" },
    garage = { filename = "garage" },
    garage_v2 = { filename = "garage_v2" },
    radial = { filename = "radial" },
    unicycle = { filename = "unicycle" }
}

local missionLayouts = {
    basicMissionLayout = { filename = "basicMission" },
    dragMission = { filename = "dragMission" },
    driftMission = { filename = "driftMission" }
}

local defaultPartyApp = {
    appName = "careermpparty",
    placement = {
        bottom = "",
        height = "560px",
        left = "0px",
        position = "absolute",
        right = "",
        top = "260px",
        width = "448px"
    }
}

local function toast(messageType, title, msg, timeout)
    guihooks.trigger('toastrMsg', {
        type = messageType,
        title = title,
        msg = msg,
        config = { timeOut = timeout or 2500 }
    })
end

local function decodeJson(data)
    if type(data) == "table" then
        return data
    end

    local ok, decoded = pcall(jsonDecode, data or "{}")
    if ok and type(decoded) == "table" then
        return decoded
    end

    return {}
end

local function isMPSession()
    return MPCoreNetwork and MPCoreNetwork.isMPSession and MPCoreNetwork.isMPSession()
end

local function sendEvent(eventName, payload)
    if not isMPSession() then
        toast("warning", "Party", "You are not connected to a multiplayer session.", 2200)
        return false
    end

    TriggerServerEvent(eventName, jsonEncode(payload or {}))
    return true
end

local function buildPlayersList()
    local playersList = {}
    if not MPVehicleGE or not MPVehicleGE.getPlayers then
        return playersList
    end

    for _, playerData in pairs(MPVehicleGE.getPlayers() or {}) do
        table.insert(playersList, {
            id = playerData.playerID or playerData.id,
            name = playerData.name,
            formattedName = playerData.formatted_name or playerData.formattedName or playerData.name,
            isSelf = playerData.name == state.selfName,
        })
    end

    table.sort(playersList, function(left, right)
        return tostring(left.name or "") < tostring(right.name or "")
    end)

    return playersList
end

local function requestState()
    if not isMPSession() then
        return
    end
    sendEvent("careerMPPartySharedVehiclesGetState", {})
end

local function rxState(data)
    local decoded = decodeJson(data)
    state.selfName = decoded.selfName or ""
    state.party = decoded.party
    state.invites = decoded.invites or {}
    state.sharedVehicles = decoded.sharedVehicles or {
        own = {},
        borrowed = {},
        ownCount = 0,
        borrowedCount = 0,
        partyTotal = 0,
    }
    state.marketplace = decoded.marketplace or {
        myListings = {},
        publicListings = {},
        listingCount = 0,
    }
    state.loaners = decoded.loaners or {
        given = {},
        received = {},
        givenCount = 0,
        receivedCount = 0,
        total = 0,
    }
    syncedOnce = true
    reconcileLoanerVehicles()
end

local function rxNotice(data)
    local decoded = decodeJson(data)
    toast("success", decoded.title or "Party", decoded.message or "Done.", 2600)
    requestState()
end

local function rxError(data)
    local decoded = decodeJson(data)
    toast("error", decoded.title or "Party", decoded.message or "Something went wrong.", 3000)
    requestState()
end

local function createParty()
    sendEvent("careerMPPartyCreate", {})
end

local function invitePlayer(targetName)
    targetName = tostring(targetName or "")
    if targetName == "" then
        toast("warning", "Party invite", "Select a valid player first.", 2400)
        return
    end
    sendEvent("careerMPPartyInvite", { targetName = targetName })
end

local function acceptInvite(fromName)
    sendEvent("careerMPPartyAcceptInvite", { fromName = fromName })
end

local function leaveParty()
    sendEvent("careerMPPartyLeave", {})
end

local function buildSharedLookup()
    local lookup = {}
    for _, vehicle in ipairs((state.sharedVehicles and state.sharedVehicles.own) or {}) do
        lookup[tostring(vehicle.inventoryId)] = vehicle
    end
    return lookup
end

local function buildMarketplaceLookup()
    local lookup = {}
    for _, listing in ipairs((state.marketplace and state.marketplace.myListings) or {}) do
        lookup[tostring(listing.inventoryId)] = listing
    end
    return lookup
end

local function buildGivenLoanLookup()
    local lookup = {}
    for _, loan in ipairs((state.loaners and state.loaners.given) or {}) do
        lookup[tostring(loan.inventoryId)] = loan
    end
    return lookup
end

local function buildReceivedLoanLookup()
    local lookup = {}
    for _, loan in ipairs((state.loaners and state.loaners.received) or {}) do
        lookup[tostring(loan.loanId)] = loan
    end
    return lookup
end

local function getInventoryVehicles()
    return career_modules_inventory and career_modules_inventory.getVehicles and career_modules_inventory.getVehicles() or {}
end

local function isPlayerLoanVehicle(vehicleInfo)
    return type(vehicleInfo) == "table" and tostring(vehicleInfo.multiplayerLoanId or "") ~= ""
end

local function removeInventoryVehicle(inventoryId)
    if not career_modules_inventory or not career_modules_inventory.removeVehicle then
        return false
    end

    career_modules_inventory.removeVehicle(tonumber(inventoryId) or inventoryId)

    if career_modules_inventory.sendDataToUi then
        career_modules_inventory.sendDataToUi()
    end
    if career_saveSystem and career_saveSystem.saveCurrent then
        career_saveSystem.saveCurrent()
    end

    return true
end

local function getMoneyBalance()
    if career_modules_playerAttributes and career_modules_playerAttributes.getAttributeValue then
        return tonumber(career_modules_playerAttributes.getAttributeValue("money")) or 0
    end
    return 0
end

local function getNextInventoryId()
    local vehicles = getInventoryVehicles()
    local nextInventoryId = 1
    while vehicles[nextInventoryId] do
        nextInventoryId = nextInventoryId + 1
    end
    return nextInventoryId
end

local function snapshotVehicleForTransfer(inventoryId)
    local vehicles = career_modules_inventory and career_modules_inventory.getVehicles and career_modules_inventory.getVehicles() or {}
    local vehicleInfo = vehicles[tonumber(inventoryId)] or vehicles[inventoryId]
    if not vehicleInfo then
        return nil
    end

    local vehicleSnapshot = deepcopy(vehicleInfo)
    vehicleSnapshot.id = nil
    vehicleSnapshot.owned = true
    vehicleSnapshot.favorite = nil
    vehicleSnapshot.loanType = nil
    vehicleSnapshot.owningOrganization = nil
    vehicleSnapshot.listedForSale = nil
    return vehicleSnapshot
end

local function importMarketplaceVehicle(vehicleData)
    if type(vehicleData) ~= "table" then
        return nil
    end

    if not career_modules_inventory or not career_modules_inventory.getVehicles then
        return nil
    end

    local vehicles = career_modules_inventory.getVehicles()
    local newInventoryId = getNextInventoryId()
    local vehicleCopy = deepcopy(vehicleData)
    vehicleCopy.id = newInventoryId
    vehicleCopy.owned = true
    vehicleCopy.favorite = nil
    vehicleCopy.loanType = nil
    vehicleCopy.owningOrganization = nil
    vehicleCopy.listedForSale = nil

    vehicles[newInventoryId] = vehicleCopy

    if career_modules_inventory.getFavoriteVehicle and not career_modules_inventory.getFavoriteVehicle() and career_modules_inventory.setFavoriteVehicle then
        career_modules_inventory.setFavoriteVehicle(newInventoryId)
    end

    if career_modules_inventory.sendDataToUi then
        career_modules_inventory.sendDataToUi()
    end

    if career_saveSystem and career_saveSystem.saveCurrent then
        career_saveSystem.saveCurrent()
    end

    return newInventoryId
end

local function importLoanVehicle(loan)
    if type(loan) ~= "table" or type(loan.vehicleData) ~= "table" then
        return nil
    end
    if not career_modules_inventory or not career_modules_inventory.getVehicles then
        return nil
    end

    local vehicles = career_modules_inventory.getVehicles()
    local newInventoryId = getNextInventoryId()
    local vehicleCopy = deepcopy(loan.vehicleData)
    vehicleCopy.id = newInventoryId
    vehicleCopy.owned = false
    vehicleCopy.favorite = nil
    vehicleCopy.loanType = "player"
    vehicleCopy.owningOrganization = nil
    vehicleCopy.listedForSale = nil
    vehicleCopy.takesNoInventorySpace = true
    vehicleCopy.multiplayerLoanId = tostring(loan.loanId or "")
    vehicleCopy.loanExpiresAt = tonumber(loan.expiresAt) or 0
    vehicleCopy.loanOwnerName = tostring(loan.ownerName or "")
    vehicleCopy.loanBorrowerName = tostring(state.selfName or "")
    vehicleCopy.niceName = tostring(loan.vehicleName or vehicleCopy.niceName or vehicleCopy.model or ("Vehicle " .. tostring(newInventoryId)))
    vehicleCopy.model = vehicleCopy.model or loan.model or ""

    vehicles[newInventoryId] = vehicleCopy

    if career_modules_inventory.sendDataToUi then
        career_modules_inventory.sendDataToUi()
    end
    if career_saveSystem and career_saveSystem.saveCurrent then
        career_saveSystem.saveCurrent()
    end

    return newInventoryId
end

reconcileLoanerVehicles = function()
    if not career_modules_inventory or not career_modules_inventory.getVehicles then
        return
    end

    local vehicles = career_modules_inventory.getVehicles() or {}
    local localLoansById = {}
    local receivedLoans = buildReceivedLoanLookup()
    local staleInventoryIds = {}

    for inventoryId, vehicleInfo in pairs(vehicles) do
        if isPlayerLoanVehicle(vehicleInfo) then
            local loanId = tostring(vehicleInfo.multiplayerLoanId or "")
            if receivedLoans[loanId] then
                localLoansById[loanId] = tonumber(inventoryId) or inventoryId
                vehicleInfo.loanType = "player"
                vehicleInfo.owned = false
                vehicleInfo.takesNoInventorySpace = true
                vehicleInfo.loanExpiresAt = tonumber(receivedLoans[loanId].expiresAt) or vehicleInfo.loanExpiresAt
                vehicleInfo.loanOwnerName = tostring(receivedLoans[loanId].ownerName or vehicleInfo.loanOwnerName or "")
                vehicleInfo.niceName = tostring(receivedLoans[loanId].vehicleName or vehicleInfo.niceName or vehicleInfo.model or ("Vehicle " .. tostring(inventoryId)))
            else
                table.insert(staleInventoryIds, inventoryId)
            end
        end
    end

    for _, inventoryId in ipairs(staleInventoryIds) do
        removeInventoryVehicle(inventoryId)
    end

    for loanId, loan in pairs(receivedLoans) do
        if not localLoansById[loanId] then
            importLoanVehicle(loan)
        end
    end
end

local function buildOwnedVehicles()
    if not career_modules_inventory or not career_modules_inventory.getVehicles then
        return {}
    end

    local vehicles = career_modules_inventory.getVehicles() or {}
    local currentVehicle = career_modules_inventory.getCurrentVehicle and career_modules_inventory.getCurrentVehicle() or nil
    local sharedLookup = buildSharedLookup()
    local marketplaceLookup = buildMarketplaceLookup()
    local givenLoanLookup = buildGivenLoanLookup()
    local ownedVehicles = {}

    for inventoryId, vehicleInfo in pairs(vehicles) do
        if type(vehicleInfo) == "table" and not isPlayerLoanVehicle(vehicleInfo) then
            local marketValue = career_modules_valueCalculator
                and career_modules_valueCalculator.getInventoryVehicleValue
                and math.floor(tonumber(career_modules_valueCalculator.getInventoryVehicleValue(inventoryId)) or 0)
                or 0
            local listing = marketplaceLookup[tostring(inventoryId)]
            local activeLoan = givenLoanLookup[tostring(inventoryId)]
            table.insert(ownedVehicles, {
                inventoryId = tostring(inventoryId),
                vehicleName = vehicleInfo.niceName or vehicleInfo.model or ("Vehicle " .. tostring(inventoryId)),
                model = vehicleInfo.model or "",
                isCurrent = currentVehicle == inventoryId,
                needsRepair = career_modules_insurance_insurance
                    and career_modules_insurance_insurance.inventoryVehNeedsRepair
                    and career_modules_insurance_insurance.inventoryVehNeedsRepair(inventoryId)
                    or false,
                isSharedWithParty = sharedLookup[tostring(inventoryId)] ~= nil,
                isListedForSale = listing ~= nil,
                isLoanedOut = activeLoan ~= nil,
                loanId = activeLoan and activeLoan.loanId or nil,
                loanBorrowerName = activeLoan and activeLoan.borrowerName or nil,
                loanExpiresAt = activeLoan and activeLoan.expiresAt or nil,
                loanSecondsRemaining = activeLoan and activeLoan.secondsRemaining or 0,
                listingId = listing and listing.listingId or nil,
                askingPrice = listing and listing.askingPrice or marketValue,
                marketValue = marketValue,
            })
        end
    end

    table.sort(ownedVehicles, function(left, right)
        if left.isCurrent ~= right.isCurrent then
            return left.isCurrent
        end
        return string.lower(left.vehicleName or "") < string.lower(right.vehicleName or "")
    end)

    return ownedVehicles
end

local function shareVehicle(inventoryId)
    local inventoryKey = tostring(inventoryId or "")
    if inventoryKey == "" then
        toast("warning", "Shared vehicles", "Select a valid vehicle first.", 2400)
        return
    end
    if not state.party then
        toast("warning", "Shared vehicles", "Create or join a party before sharing vehicles.", 2600)
        return
    end

    local vehicles = career_modules_inventory and career_modules_inventory.getVehicles and career_modules_inventory.getVehicles() or {}
    local vehicleInfo = vehicles[tonumber(inventoryId)] or vehicles[inventoryId]
    if not vehicleInfo then
        toast("error", "Shared vehicles", "That vehicle was not found in your local inventory.", 2800)
        return
    end

    sendEvent("careerMPPartyShareVehicle", {
        inventoryId = inventoryKey,
        vehicleName = vehicleInfo.niceName or vehicleInfo.model or ("Vehicle " .. inventoryKey),
        model = vehicleInfo.model or "",
    })
end

local function revokeVehicle(inventoryId)
    local inventoryKey = tostring(inventoryId or "")
    if inventoryKey == "" then
        toast("warning", "Shared vehicles", "Select a valid vehicle first.", 2400)
        return
    end
    sendEvent("careerMPPartyRevokeVehicle", { inventoryId = inventoryKey })
end

local function listVehicle(inventoryId, askingPrice)
    local inventoryKey = tostring(inventoryId or "")
    local vehicleSnapshot = snapshotVehicleForTransfer(inventoryKey)
    if inventoryKey == "" or not vehicleSnapshot then
        toast("error", "Marketplace", "That vehicle could not be listed.", 2600)
        return
    end

    local price = math.max(1, math.floor(tonumber(askingPrice) or 0))
    if price <= 0 then
        toast("warning", "Marketplace", "Choose a valid asking price.", 2400)
        return
    end

    sendEvent("careerMPPartyListVehicle", {
        inventoryId = inventoryKey,
        askingPrice = price,
        vehicleName = vehicleSnapshot.niceName or vehicleSnapshot.model or ("Vehicle " .. inventoryKey),
        model = vehicleSnapshot.model or "",
        vehicleData = vehicleSnapshot,
    })
end

local function delistVehicle(listingId)
    local listingKey = tostring(listingId or "")
    if listingKey == "" then
        toast("warning", "Marketplace", "Select a valid listing first.", 2400)
        return
    end
    sendEvent("careerMPPartyDelistVehicle", { listingId = listingKey })
end

local function buyListing(listingId)
    local listingKey = tostring(listingId or "")
    if listingKey == "" then
        toast("warning", "Marketplace", "Select a valid listing first.", 2400)
        return
    end
    sendEvent("careerMPPartyBuyListing", { listingId = listingKey })
end

local function grantLoan(inventoryId, borrowerName, durationMinutes)
    local inventoryKey = tostring(inventoryId or "")
    local vehicleSnapshot = snapshotVehicleForTransfer(inventoryKey)
    if inventoryKey == "" or not vehicleSnapshot then
        toast("error", "Temporary keys", "That vehicle could not be prepared for a temporary key grant.", 2800)
        return
    end

    local targetName = tostring(borrowerName or "")
    if targetName == "" then
        toast("warning", "Temporary keys", "Choose a player to receive the temporary keys.", 2400)
        return
    end

    local duration = math.max(1, math.floor(tonumber(durationMinutes) or 0))
    sendEvent("careerMPPartyGrantLoan", {
        inventoryId = inventoryKey,
        borrowerName = targetName,
        durationMinutes = duration,
        vehicleName = vehicleSnapshot.niceName or vehicleSnapshot.model or ("Vehicle " .. inventoryKey),
        model = vehicleSnapshot.model or "",
        vehicleData = vehicleSnapshot,
    })
end

local function revokeLoan(loanId)
    local loanKey = tostring(loanId or "")
    if loanKey == "" then
        toast("warning", "Temporary keys", "Select a valid temporary key grant first.", 2400)
        return
    end
    sendEvent("careerMPPartyRevokeLoan", { loanId = loanKey })
end

local function returnLoan(loanId)
    local loanKey = tostring(loanId or "")
    if loanKey == "" then
        toast("warning", "Temporary keys", "Select a valid borrowed vehicle first.", 2400)
        return
    end
    sendEvent("careerMPPartyReturnLoan", { loanId = loanKey })
end

local function rxPreparePurchase(data)
    local decoded = decodeJson(data)
    local pendingSaleId = tostring(decoded.pendingSaleId or "")
    local askingPrice = math.max(0, math.floor(tonumber(decoded.askingPrice) or 0))

    if pendingSaleId == "" then
        return
    end
    if getMoneyBalance() < askingPrice then
        sendEvent("careerMPPartySaleBuyerAbort", {
            pendingSaleId = pendingSaleId,
            reason = "You do not have enough money to buy " .. tostring(decoded.vehicleName or "that vehicle") .. ".",
        })
        return
    end
    if career_modules_inventory and career_modules_inventory.hasFreeSlot and not career_modules_inventory.hasFreeSlot() then
        sendEvent("careerMPPartySaleBuyerAbort", {
            pendingSaleId = pendingSaleId,
            reason = "You do not have a free garage slot for that purchase.",
        })
        return
    end

    sendEvent("careerMPPartySaleBuyerReady", { pendingSaleId = pendingSaleId })
end

local function rxPrepareSale(data)
    local decoded = decodeJson(data)
    local pendingSaleId = tostring(decoded.pendingSaleId or "")
    local inventoryId = tostring(decoded.inventoryId or "")
    local vehicleSnapshot = snapshotVehicleForTransfer(inventoryId)

    if pendingSaleId == "" then
        return
    end
    if not vehicleSnapshot then
        sendEvent("careerMPPartySaleSellerAbort", {
            pendingSaleId = pendingSaleId,
            reason = tostring(decoded.vehicleName or "The listed vehicle") .. " is no longer in your inventory.",
        })
        return
    end

    sendEvent("careerMPPartySaleSellerReady", {
        pendingSaleId = pendingSaleId,
        vehicleData = vehicleSnapshot,
    })
end

local function rxFinalizePurchase(data)
    local decoded = decodeJson(data)
    local pendingSaleId = tostring(decoded.pendingSaleId or "")
    if pendingSaleId == "" or processedMarketTransactions[pendingSaleId] then
        return
    end

    local askingPrice = math.max(0, math.floor(tonumber(decoded.askingPrice) or 0))
    local importedInventoryId = importMarketplaceVehicle(decoded.vehicleData)
    if not importedInventoryId then
        toast("error", "Marketplace", "The purchased vehicle could not be imported into your inventory.", 3200)
        return
    end

    if career_modules_playerAttributes and career_modules_playerAttributes.addAttributes then
        career_modules_playerAttributes.addAttributes(
            { money = -askingPrice },
            { tags = { "marketplace", "vehiclePurchase", "multiplayer" }, label = "Bought " .. tostring(decoded.vehicleName or "a vehicle") .. " from " .. tostring(decoded.sellerName or "another player") }
        )
    end

    processedMarketTransactions[pendingSaleId] = true
    requestState()
end

local function rxFinalizeSale(data)
    local decoded = decodeJson(data)
    local pendingSaleId = tostring(decoded.pendingSaleId or "")
    if pendingSaleId == "" or processedMarketTransactions[pendingSaleId] then
        return
    end

    local inventoryId = tonumber(decoded.inventoryId) or decoded.inventoryId
    local askingPrice = math.max(0, math.floor(tonumber(decoded.askingPrice) or 0))

    if career_modules_inventory and career_modules_inventory.removeVehicle then
        career_modules_inventory.removeVehicle(inventoryId)
    end

    if career_modules_playerAttributes and career_modules_playerAttributes.addAttributes then
        career_modules_playerAttributes.addAttributes(
            { money = askingPrice },
            { tags = { "marketplace", "vehicleSold", "multiplayer" }, label = "Sold " .. tostring(decoded.vehicleName or "a vehicle") .. " to " .. tostring(decoded.buyerName or "another player") }
        )
    end

    if career_saveSystem and career_saveSystem.saveCurrent then
        career_saveSystem.saveCurrent()
    end
    if career_modules_inventory and career_modules_inventory.sendDataToUi then
        career_modules_inventory.sendDataToUi()
    end

    processedMarketTransactions[pendingSaleId] = true
    requestState()
end

local function printState()
    log("I", "careerMPPartySharedVehicles", "Party state: " .. jsonEncode(state))
end

local function help()
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.createParty()')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.invitePlayer("PlayerName")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.acceptInvite("LeaderName")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.leaveParty()')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.shareVehicle("123")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.revokeVehicle("123")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.listVehicle("123", 15000)')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.buyListing("5")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.delistVehicle("5")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.grantLoan("123", "PlayerName", 30)')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.revokeLoan("7")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.returnLoan("7")')
    log("I", "careerMPPartySharedVehicles", 'extensions.careerMPPartySharedVehicles.printState()')
end

local function placementsMatch(leftPlacement, rightPlacement)
    return jsonEncode(leftPlacement or {}) == jsonEncode(rightPlacement or {})
end

local function parsePlacementPixels(value)
    if type(value) == "number" then
        return value
    end
    if type(value) ~= "string" then
        return nil
    end
    return tonumber(value:match("^%s*(-?[%d%.]+)"))
end

local function normalizePartyPlacement(placement)
    local normalizedPlacement = deepcopy(placement or {})
    local width = parsePlacementPixels(normalizedPlacement.width)
    local height = parsePlacementPixels(normalizedPlacement.height)

    if not width or width < 220 then
        normalizedPlacement.width = defaultPartyApp.placement.width
    end
    if not height or height < 140 then
        normalizedPlacement.height = defaultPartyApp.placement.height
    end

    normalizedPlacement.position = normalizedPlacement.position or defaultPartyApp.placement.position
    return normalizedPlacement
end

local function ensureApp(layout, appData)
    layout.apps = layout.apps or {}

    local firstIndex = nil
    local removed = false
    for i = #layout.apps, 1, -1 do
        local app = layout.apps[i]
        if app.appName == appData.appName then
            if not firstIndex then
                firstIndex = i
            else
                table.remove(layout.apps, i)
                removed = true
            end
        end
    end

    if not firstIndex then
        table.insert(layout.apps, deepcopy(appData))
        return true
    end

    local existingApp = layout.apps[firstIndex]
    local desiredPlacement = normalizePartyPlacement(existingApp.placement or appData.placement)
    if not placementsMatch(existingApp.placement, desiredPlacement) then
        layout.apps[firstIndex].placement = desiredPlacement
        return true
    end

    return removed
end

local function loadLayout(customDir, defaultDir, filename)
    local custom = jsonReadFile(customDir .. filename .. ".uilayout.json")
    if custom then
        return deepcopy(custom), customDir
    end

    local default = jsonReadFile(defaultDir .. filename .. ".uilayout.json")
    if default then
        return deepcopy(default), customDir
    end
end

local function checkUIApps(gameState)
    if not gameState or not gameState.appLayout then
        return
    end

    local layoutInfo = defaultLayouts[gameState.appLayout] or missionLayouts[gameState.appLayout]
    if not layoutInfo then
        return
    end

    local customDir = defaultLayouts[gameState.appLayout] and userDefaultAppLayoutDirectory or userMissionAppLayoutDirectory
    local defaultDir = defaultLayouts[gameState.appLayout] and defaultAppLayoutDirectory or missionAppLayoutDirectory
    local layout, saveDir = loadLayout(customDir, defaultDir, layoutInfo.filename)
    if not layout then
        return
    end

    if ensureApp(layout, defaultPartyApp) then
        jsonWriteFile(saveDir .. layoutInfo.filename .. ".uilayout.json", layout, 1)
        layoutRefreshRequested = true
    end
end

local function getUiState()
    return {
        selfName = state.selfName,
        party = deepcopy(state.party),
        invites = deepcopy(state.invites),
        sharedVehicles = deepcopy(state.sharedVehicles),
        marketplace = deepcopy(state.marketplace),
        loaners = deepcopy(state.loaners),
        players = buildPlayersList(),
        ownedVehicles = buildOwnedVehicles(),
        syncedOnce = syncedOnce,
    }
end

local function onGameStateUpdate(gameState)
    checkUIApps(gameState)
end

local function onWorldReadyState(worldState)
    if worldState == 2 then
        requestState()
    end
end

local function onUpdate(dtReal, dtSim, dtRaw)
    if layoutRefreshRequested and ui_apps and ui_apps.requestUIAppsData then
        ui_apps.requestUIAppsData()
        layoutRefreshRequested = false
    end
end

local function onExtensionLoaded()
    AddEventHandler("careerMPPartySharedVehiclesRxState", rxState)
    AddEventHandler("careerMPPartySharedVehiclesRxNotice", rxNotice)
    AddEventHandler("careerMPPartySharedVehiclesRxError", rxError)
    AddEventHandler("careerMPPartyDealershipPreparePurchase", rxPreparePurchase)
    AddEventHandler("careerMPPartyDealershipPrepareSale", rxPrepareSale)
    AddEventHandler("careerMPPartyDealershipFinalizePurchase", rxFinalizePurchase)
    AddEventHandler("careerMPPartyDealershipFinalizeSale", rxFinalizeSale)
    if worldReadyState == 2 then
        requestState()
    end
    log("I", "careerMPPartySharedVehicles", "Party client module loaded")
end

local function onExtensionUnloaded()
    log("I", "careerMPPartySharedVehicles", "Party client module unloaded")
end

M.requestState = requestState
M.createParty = createParty
M.invitePlayer = invitePlayer
M.acceptInvite = acceptInvite
M.leaveParty = leaveParty
M.shareVehicle = shareVehicle
M.revokeVehicle = revokeVehicle
M.listVehicle = listVehicle
M.delistVehicle = delistVehicle
M.buyListing = buyListing
M.grantLoan = grantLoan
M.revokeLoan = revokeLoan
M.returnLoan = returnLoan
M.printState = printState
M.help = help
M.getUiState = getUiState

M.onGameStateUpdate = onGameStateUpdate
M.onWorldReadyState = onWorldReadyState
M.onUpdate = onUpdate
M.onExtensionLoaded = onExtensionLoaded
M.onExtensionUnloaded = onExtensionUnloaded

M.onInit = function()
    setExtensionUnloadMode(M, 'manual')
end

return M
