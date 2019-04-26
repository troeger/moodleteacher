import java.util.Arrays;
import java.lang.Math; 

public class Kniffel {

	public static void main(String[] args) {
		int erstWuerf = 0;
		int zweitWuerf = 0;
		int drittWuerf = 0;
		int viertWuerf= 0;
		int fuenftWuerf= 0;
		if (0 == Integer.parseInt(args[0])) {
			erstWuerf = (int)(Math.random()*6+1);
			zweitWuerf = (int)(Math.random()*6+1);
			drittWuerf = (int)(Math.random()*6+1);
			viertWuerf = (int)(Math.random()*6+1);
			fuenftWuerf = (int)(Math.random()*6+1);
		} else {
		erstWuerf = Integer.parseInt(args[0]);
		zweitWuerf = Integer.parseInt(args[1]);
		drittWuerf = Integer.parseInt(args[2]);
		viertWuerf = Integer.parseInt(args[3]);
		fuenftWuerf = Integer.parseInt(args[4]);
		}
		int [] wuerfelhash = {erstWuerf, zweitWuerf, drittWuerf, viertWuerf, fuenftWuerf};
		Arrays.sort(wuerfelhash);
		
// Ungültige Werte
		int nr = 0;
		while (nr < wuerfelhash.length) {
			if(wuerfelhash[nr] > 6.9) {
				int wuerfelnummer = nr + 1;
				System.out.println("Ungültiger Wert für Würfel " + wuerfelnummer);
				return;
			} else {
				nr++;
			}
		}
	
// Ausgabe
		for(int index = 0; index < wuerfelhash.length; index++) {
			System.out.print(wuerfelhash[index] + "    ");
		}
		System.out.println();
		System.out.println();

// Wuerfelsumme
		int summe = 0;
		for(int i = 0; i < wuerfelhash.length; i++) {
			summe = summe + wuerfelhash[i];
			if(i == 4) {
				System.out.println("Wurfsumme: " + summe);
			}
		}

// Kniffel
		if((erstWuerf == zweitWuerf) && (zweitWuerf == drittWuerf) && (drittWuerf == viertWuerf) && (viertWuerf== fuenftWuerf)) {
			System.out.println("Kniffel: ja" + "          " + "Punkte: 50");	
			} else {
			System.out.println("Kniffel: nein");	
			}
		
// Dreier Pasch
		int count = 0;
		for(int i = 0; i < (wuerfelhash.length-1); i++) {
		if(wuerfelhash[i] == wuerfelhash[(i+1)]) {
				count++;
				if (count == 3) {
					break;
				}
			}
		}
			if (count == 3) {
				System.out.println("Dreierpasch: Ja" + "           " + "Punkte: 10 ");
			} else {
				System.out.println("Dreierpasch: nein");
			}
			
// Vierer Pasch
			int counter = 0;
			int counter2 = 0;
			int counter3 = 0;
			int counter4 = 0;
			int counter5 = 0;
			int counter6 = 0;

			for(int i = 0; i < (wuerfelhash.length-1); i++) {
			 if (wuerfelhash[i] == 1 ) {
				 counter++;
			 } else if (wuerfelhash[i] == 2 ) {
				 counter2++;
			 } else if (wuerfelhash[i] == 3 ) {
				 counter3++;
			 } else if (wuerfelhash[i] == 4 ) {
				 counter4++;
			 } else if (wuerfelhash[i] == 5 ) {
				 counter5++;
			 } else if (wuerfelhash[i] == 6 ) {
				 counter6++;
			 }
			}
			 if((counter == 4) | (counter2 == 4) | (counter3 == 4)| (counter4 == 4) | (counter5 == 4) | (counter6 ==4)) {
				 System.out.println("Viererpasch: ja" + "           " + "Punkte: 15");
			 } else {
				 System.out.println("Viererpasch: nein");
			 }
			
// Straße
		int gleiche = 0;
		int coun = 0;
			for(int i = 0; i < wuerfelhash.length-1; i++) {
			if (wuerfelhash[i+1] - wuerfelhash[i] == 1){
						coun++;
					} else if (wuerfelhash[i] == wuerfelhash[i+1]) {
						gleiche++;
					}
				}
					if((coun == 4) && (gleiche == 0)) {
						System.out.println("Große Straße: ja" + "           " + "Punkte: 40");
					} else if ((coun == 3) && (gleiche <= 1)) {
						System.out.println("Kleine Straße: ja" + "           " + "Punkte: 30");
						System.out.println("Große Straße: nein");				
					} else {
						System.out.println("Große Straße: nein");
						System.out.println("Kleine Straße: nein");
					}
					
// FullHouse
					int cou = 0;
					for(int i = 0; i <= 1; i++) {
						if(wuerfelhash[i] == wuerfelhash[(i+1)]) {
							cou++;
						}
					}
					if ((cou == 2) && (wuerfelhash[3] == wuerfelhash[4])) {
						System.out.println("Fullhouse: ja" + "           " + "Punkte: 25");
					} else if ((cou == 1) && (wuerfelhash[2] == wuerfelhash[3]) && (wuerfelhash[3]== wuerfelhash[4])) {
						System.out.println("Fullhouse: ja"+ "           " + "Punkte: 25" );
					} else {
						System.out.println("Fullhouse: nein");
					}
				
	} // main
} //class
