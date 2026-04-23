var app = angular.module('beamng.apps');

app.directive('careermpparty', [function () {
	return {
		templateUrl: '/ui/modules/apps/CareerMP-Party/app.html',
		replace: true,
		restrict: 'EA',
		scope: true
	};
}]);

app.controller('CareerMPPartyController', ['$scope', '$interval', function ($scope, $interval) {
	const panelTransitionMs = 180;
	const tabStorageKey = 'careermpPartyActiveTab';
	let hidePanelTimer = null;

	$scope.party = null;
	$scope.invites = [];
	$scope.players = [];
	$scope.onlinePlayers = [];
	$scope.ownedVehicles = [];
	$scope.sharedVehicles = { own: [], borrowed: [], ownCount: 0, borrowedCount: 0, partyTotal: 0 };
	$scope.marketplace = { myListings: [], publicListings: [], listingCount: 0 };
	$scope.loaners = { given: [], received: [], givenCount: 0, receivedCount: 0, total: 0 };
	$scope.loanDraft = { inventoryId: '', borrowerName: '', durationMinutes: 30 };
	$scope.activeTab = localStorage.getItem(tabStorageKey) || 'dealership';
	$scope.syncedOnce = false;

	function normalizeTab(tabName) {
		if (tabName === 'party' || tabName === 'dealership' || tabName === 'loaners') {
			return tabName;
		}
		return 'dealership';
	}

	function clearHidePanelTimer() {
		if (!hidePanelTimer) {
			return;
		}
		clearTimeout(hidePanelTimer);
		hidePanelTimer = null;
	}

	function updateButtonHeight() {
		const root = document.querySelector('.careermp-party-root');
		const button = document.getElementById('party-show-button');
		if (!root || !button) {
			return;
		}

		const isVerticalDock = root.classList.contains('is-left-anchored') || root.classList.contains('is-right-anchored');
		button.style.width = isVerticalDock ? '28px' : '75px';
		button.style.height = isVerticalDock ? '75px' : '28px';
	}

	function setDockSide(side) {
		const root = document.querySelector('.careermp-party-root');
		if (!root) {
			return;
		}

		root.classList.toggle('is-left-anchored', side === 'left');
		root.classList.toggle('is-right-anchored', side === 'right');
		root.classList.toggle('is-top-anchored', side === 'top');
		root.classList.toggle('is-bottom-anchored', side === 'bottom');
	}

	function updateDockOrientation() {
		const root = document.querySelector('.careermp-party-root');
		if (!root || !window.innerWidth || !window.innerHeight) {
			return;
		}

		const rect = root.getBoundingClientRect();
		const distances = [
			{ side: 'left', distance: rect.left },
			{ side: 'right', distance: window.innerWidth - rect.right },
			{ side: 'top', distance: rect.top },
			{ side: 'bottom', distance: window.innerHeight - rect.bottom }
		];

		distances.sort(function (left, right) {
			return left.distance - right.distance;
		});

		setDockSide(distances[0].side);
		updateButtonHeight();
	}

	function showPanel() {
		const container = document.getElementById('party-container');
		const button = document.getElementById('party-show-button');
		if (!container || !button) {
			return;
		}

		clearHidePanelTimer();
		container.style.display = 'block';
		updateDockOrientation();
		void container.offsetWidth;
		container.classList.add('is-open');
		button.textContent = 'P';
		localStorage.setItem('careermpPartyShown', '1');
		refreshState();
		setTimeout(updateButtonHeight, 0);
	}

	function hidePanel(immediate) {
		const container = document.getElementById('party-container');
		const button = document.getElementById('party-show-button');
		if (!container || !button) {
			return;
		}

		clearHidePanelTimer();
		container.classList.remove('is-open');
		button.textContent = 'P';
		updateButtonHeight();
		localStorage.setItem('careermpPartyShown', '0');
		setCefFocus(false);

		if (immediate) {
			container.style.display = 'none';
			return;
		}

		hidePanelTimer = setTimeout(function () {
			if (!container.classList.contains('is-open')) {
				container.style.display = 'none';
			}
			hidePanelTimer = null;
		}, panelTransitionMs);
	}

	function setCefFocus(focused) {
		bngApi.engineLua('setCEFFocus(' + (focused ? 'true' : 'false') + ')');
	}

	function applyState(data) {
		let parsed = data;
		if (typeof parsed === 'string') {
			try {
				parsed = JSON.parse(parsed);
			} catch (error) {
				return;
			}
		}

		if (!parsed) {
			return;
		}

		$scope.party = parsed.party || null;
		$scope.invites = Array.isArray(parsed.invites) ? parsed.invites : [];
		$scope.players = Array.isArray(parsed.players) ? parsed.players : [];
		$scope.onlinePlayers = $scope.players;
		$scope.ownedVehicles = Array.isArray(parsed.ownedVehicles) ? parsed.ownedVehicles : [];
		$scope.sharedVehicles = parsed.sharedVehicles || { own: [], borrowed: [], ownCount: 0, borrowedCount: 0, partyTotal: 0 };
		$scope.marketplace = parsed.marketplace || { myListings: [], publicListings: [], listingCount: 0 };
		$scope.loaners = parsed.loaners || { given: [], received: [], givenCount: 0, receivedCount: 0, total: 0 };

		if (!Array.isArray($scope.sharedVehicles.own)) {
			$scope.sharedVehicles.own = [];
		}
		if (!Array.isArray($scope.sharedVehicles.borrowed)) {
			$scope.sharedVehicles.borrowed = [];
		}
		if (!Array.isArray($scope.marketplace.myListings)) {
			$scope.marketplace.myListings = [];
		}
		if (!Array.isArray($scope.marketplace.publicListings)) {
			$scope.marketplace.publicListings = [];
		}
		if (!Array.isArray($scope.loaners.given)) {
			$scope.loaners.given = [];
		}
		if (!Array.isArray($scope.loaners.received)) {
			$scope.loaners.received = [];
		}

		$scope.ownedVehicles.forEach(function (vehicle) {
			if (vehicle.askingPriceInput === undefined || vehicle.askingPriceInput === null || vehicle.askingPriceInput === '') {
				vehicle.askingPriceInput = Number(vehicle.askingPrice || vehicle.marketValue || 0) || 0;
			}
		});

		const grantableVehicles = $scope.ownedVehicles.filter(function (vehicle) {
			return !vehicle.isLoanedOut && !vehicle.isListedForSale;
		});
		if (!grantableVehicles.some(function (vehicle) { return String(vehicle.inventoryId) === String($scope.loanDraft.inventoryId || ''); })) {
			$scope.loanDraft.inventoryId = grantableVehicles.length ? String(grantableVehicles[0].inventoryId) : '';
		}

		const eligiblePlayers = $scope.players.filter(function (player) {
			return !player.isSelf;
		});
		if (!eligiblePlayers.some(function (player) { return String(player.name || '') === String($scope.loanDraft.borrowerName || ''); })) {
			$scope.loanDraft.borrowerName = eligiblePlayers.length ? String(eligiblePlayers[0].name || '') : '';
		}
		if (!$scope.loanDraft.durationMinutes || Number($scope.loanDraft.durationMinutes) <= 0) {
			$scope.loanDraft.durationMinutes = 30;
		}

		$scope.activeTab = normalizeTab($scope.activeTab);
		$scope.syncedOnce = parsed.syncedOnce === true;
		$scope.$evalAsync();
		setTimeout(function () {
			updateDockOrientation();
		}, 0);
	}

	function refreshState() {
		bngApi.engineLua('careerMPPartySharedVehicles.getUiState()', applyState);
	}

	$scope.togglePanel = function () {
		if (localStorage.getItem('careermpPartyShown') === '1') {
			hidePanel();
		} else {
			showPanel();
		}
	};

	$scope.engageFocus = function () {
		setCefFocus(true);
	};

	$scope.releaseFocus = function () {
		setCefFocus(false);
	};

	$scope.setTab = function (tabName) {
		$scope.activeTab = normalizeTab(tabName);
		localStorage.setItem(tabStorageKey, $scope.activeTab);
	};

	$scope.isTab = function (tabName) {
		return $scope.activeTab === normalizeTab(tabName);
	};

	$scope.getDisplayName = function (player) {
		return player.formattedName || player.formatted_name || player.name || ('Player ' + player.id);
	};

	$scope.formatMoney = function (value) {
		const amount = Number(value) || 0;
		return '$' + amount.toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		});
	};

	$scope.formatRemaining = function (seconds) {
		const totalSeconds = Math.max(0, Number(seconds) || 0);
		const hours = Math.floor(totalSeconds / 3600);
		const minutes = Math.floor((totalSeconds % 3600) / 60);
		const remainingSeconds = totalSeconds % 60;

		if (hours > 0) {
			return hours + 'h ' + minutes + 'm';
		}
		if (minutes > 0) {
			return minutes + 'm ' + remainingSeconds + 's';
		}
		return remainingSeconds + 's';
	};

	$scope.loanEligiblePlayers = function () {
		return $scope.onlinePlayers.filter(function (player) {
			return !player.isSelf;
		});
	};

	$scope.grantableLoanVehicles = function () {
		return $scope.ownedVehicles.filter(function (vehicle) {
			return !vehicle.isLoanedOut && !vehicle.isListedForSale;
		});
	};

	$scope.isCurrentMember = function (player) {
		if (!$scope.party || !$scope.party.members || !player) {
			return false;
		}
		return $scope.party.members.some(function (member) {
			return member.name === player.name;
		});
	};

	$scope.canInvite = function (player) {
		if (!player || player.name === undefined || player.name === null) {
			return false;
		}
		if (player.name === '' || player.isSelf) {
			return false;
		}
		if (!$scope.party || !$scope.party.isOwner) {
			return false;
		}
		if ($scope.isCurrentMember(player)) {
			return false;
		}
		return true;
	};

	$scope.createParty = function () {
		bngApi.engineLua('careerMPPartySharedVehicles.createParty()');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.canShareVehicle = function (vehicle) {
		return !!(vehicle && $scope.party && !vehicle.isSharedWithParty && !vehicle.isLoanedOut);
	};

	$scope.canRevokeVehicle = function (vehicle) {
		return !!(vehicle && $scope.party && vehicle.isSharedWithParty);
	};

	$scope.canListVehicle = function (vehicle) {
		return !!(vehicle && !vehicle.isListedForSale && !vehicle.isLoanedOut);
	};

	$scope.canDelistVehicle = function (vehicle) {
		return !!(vehicle && vehicle.isListedForSale && vehicle.listingId);
	};

	$scope.invitePlayer = function (player) {
		if (!$scope.canInvite(player)) {
			return;
		}
		const escapedName = String(player.name || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.invitePlayer("' + escapedName + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.shareVehicle = function (vehicle) {
		if (!$scope.canShareVehicle(vehicle)) {
			return;
		}
		const escapedInventoryId = String(vehicle.inventoryId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.shareVehicle("' + escapedInventoryId + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.revokeVehicle = function (vehicle) {
		if (!$scope.canRevokeVehicle(vehicle)) {
			return;
		}
		const escapedInventoryId = String(vehicle.inventoryId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.revokeVehicle("' + escapedInventoryId + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.listVehicle = function (vehicle) {
		if (!$scope.canListVehicle(vehicle)) {
			return;
		}
		const escapedInventoryId = String(vehicle.inventoryId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		const askingPrice = parseInt(vehicle.askingPriceInput, 10);
		bngApi.engineLua('careerMPPartySharedVehicles.listVehicle("' + escapedInventoryId + '", ' + (Number.isFinite(askingPrice) ? askingPrice : 0) + ')');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.delistListing = function (listing) {
		if (!listing || !listing.listingId) {
			return;
		}
		const escapedListingId = String(listing.listingId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.delistVehicle("' + escapedListingId + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.buyListing = function (listing) {
		if (!listing || !listing.listingId || listing.isOwn) {
			return;
		}
		const escapedListingId = String(listing.listingId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.buyListing("' + escapedListingId + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.canGrantLoan = function () {
		return !!($scope.loanDraft.inventoryId && $scope.loanDraft.borrowerName && Number($scope.loanDraft.durationMinutes) > 0);
	};

	$scope.grantLoan = function () {
		if (!$scope.canGrantLoan()) {
			return;
		}
		const escapedInventoryId = String($scope.loanDraft.inventoryId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		const escapedBorrowerName = String($scope.loanDraft.borrowerName || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		const durationMinutes = parseInt($scope.loanDraft.durationMinutes, 10);
		bngApi.engineLua('careerMPPartySharedVehicles.grantLoan("' + escapedInventoryId + '", "' + escapedBorrowerName + '", ' + (Number.isFinite(durationMinutes) ? durationMinutes : 0) + ')');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.revokeLoan = function (loan) {
		if (!loan || !loan.loanId) {
			return;
		}
		const escapedLoanId = String(loan.loanId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.revokeLoan("' + escapedLoanId + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.returnLoan = function (loan) {
		if (!loan || !loan.loanId) {
			return;
		}
		const escapedLoanId = String(loan.loanId || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.returnLoan("' + escapedLoanId + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.acceptInvite = function (fromName) {
		const escapedName = String(fromName || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
		bngApi.engineLua('careerMPPartySharedVehicles.acceptInvite("' + escapedName + '")');
		refreshState();
		setTimeout(refreshState, 250);
	};

	$scope.leaveParty = function () {
		bngApi.engineLua('careerMPPartySharedVehicles.leaveParty()');
		refreshState();
		setTimeout(refreshState, 250);
	};

	const refreshTimer = $interval(refreshState, 1000);
	const dockTimer = $interval(updateDockOrientation, 250);
	refreshState();
	setTimeout(function () {
		updateDockOrientation();
		hidePanel(true);
	}, 0);

	$scope.$on('$destroy', function () {
		clearHidePanelTimer();
		setCefFocus(false);
		$interval.cancel(refreshTimer);
		$interval.cancel(dockTimer);
	});
}]);
