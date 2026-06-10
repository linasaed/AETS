within ;
package DysonModel
  package Components

    model Heizdraht
      // Vereinfachtes Modell des Heizdrahts eines Haarföhns.
      // Elektrische Leistung wird in Wärme umgewandelt.
      // Der Heizdraht besitzt eine thermische Kapazität und gibt Wärme über den HeatPort ab.
      // Bei Überschreitung von T_sicherheit wird die Heizleistung abgeschaltet (Thermosicherung).

      parameter Modelica.Units.SI.Power P_max = 1600
        "Maximale Heizleistung in W; Quelle: Dyson Supersonic Spezifikation, Power/Wattage = 1600 W";

      parameter Modelica.Units.SI.HeatCapacity C_H = 50
        "Thermische Kapazität des Heizdrahts in J/K; Modellannahme, da keine öffentliche Dyson-Angabe verfügbar";

      parameter Modelica.Units.SI.Temperature T_start = 293.15
        "Starttemperatur in K; Modellannahme: Raumtemperatur 20 °C";

      parameter Modelica.Units.SI.Temperature T_sicherheit = 423.15
        "Sicherheitsabschalttemperatur in K; entspricht 150 °C; Modellannahme für Thermosicherung";

      Modelica.Blocks.Interfaces.RealInput u_regler
        "Reglersignal 0..1: 0 = aus, 1 = maximale Heizleistung"
        annotation (Placement(
          transformation(extent={{-120,-20},{-80,20}}),
          iconTransformation(extent={{-120,-20},{-80,20}})));

      Modelica.Units.SI.Power P
        "Aktuelle Heizleistung in W";

      Modelica.Units.SI.Temperature T_H(start=T_start)
        "Temperatur des Heizdrahts";

      Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a port
        "Thermischer Anschluss zur Wärmeabgabe"
        annotation (Placement(
          transformation(extent={{90,-10},{110,10}}),
          iconTransformation(extent={{90,-10},{110,10}})));

    equation
      // Sicherheitsabschaltung: Wird T_sicherheit überschritten, geht P auf 0.
      // Dadurch simuliert das Modell das Verhalten einer realen Thermosicherung.
      P = if T_H < T_sicherheit then u_regler * P_max else 0;

      // Energiebilanz des Heizdrahts:
      // P erwärmt den Heizdraht.
      // port.Q_flow ist negativ, wenn Wärme aus dem Heizdraht in das Netzwerk abfließt.
      C_H * der(T_H) = P + port.Q_flow;
      port.T = T_H;

    end Heizdraht;

    model Motor
      // Vereinfachtes dynamisches Motormodell eines Haarföhns.
      //
      // Der Motor wird nicht elektromagnetisch oder mechanisch detailliert modelliert.
      // Stattdessen wird die gewählte Luftstromstufe in eine Soll-Drehzahl umgerechnet.
      // Die tatsächliche Motordrehzahl nähert sich dieser Soll-Drehzahl über eine
      // Zeitkonstante an (Dynamik erster Ordnung).
      //
      // Begründung:
      // Beim realen Dyson Supersonic kann der Nutzer mehrere Luftstromstufen wählen.
      // Die genaue interne Motorregelung, Wicklungswiderstände, Induktivitäten,
      // Drehmomentkonstanten und Rotorträgheiten sind öffentlich nicht verfügbar.
      // Daher wird kein vollständiges BLDC-/PMSM-Motormodell verwendet.

      parameter Integer fanLevel(min=1, max=3) = 3
        "Luftstromstufe: 1=niedrig, 2=mittel, 3=hoch; Quelle: Dyson Supersonic: 3 Speed/Airflow Settings";

      parameter Real n_max = 110000
        "Maximale Drehzahl in rpm; Quelle: Dyson Digital Motor V9, ca. 110000 rpm";

      parameter Modelica.Units.SI.Time tau_motor = 0.3
        "Motor-Zeitkonstante in s; Modellannahme für schnelles Anlaufverhalten, da keine öffentliche Dyson-Angabe verfügbar";

      Modelica.Blocks.Interfaces.RealOutput n
        "Motordrehzahl in rpm"
        annotation (Placement(
          transformation(extent={{100,-10},{120,10}}),
          iconTransformation(extent={{100,-10},{120,10}})));

    protected
      Real speedFactor
        "Relativer Drehzahlfaktor der gewählten Luftstromstufe; Modellannahme";

      Real n_soll
        "Soll-Drehzahl in rpm";

    equation
      // Vereinfachte Zuordnung der drei Luftstromstufen.
      // Dyson nennt 3 Luftstromstufen, veröffentlicht aber keine exakten Drehzahlen je Stufe.
      // Daher werden plausible relative Faktoren angenommen.
      speedFactor =
        if fanLevel == 1 then 0.4
        else if fanLevel == 2 then 0.7
        else 1.0;

      // Soll-Drehzahl aus maximaler Drehzahl und Stufenfaktor.
      n_soll = speedFactor * n_max;

      // Dynamik erster Ordnung:
      // Die Motordrehzahl springt nicht sofort auf den Sollwert,
      // sondern nähert sich diesem mit der Zeitkonstante tau_motor an.
      tau_motor * der(n) = n_soll - n;

    end Motor;

    model Propeller
      // Vereinfachtes Propellermodell eines Haarföhns.
      // Der Propeller wandelt die Motordrehzahl in einen Luftmassenstrom um.
      //
      // Modellvereinfachung:
      // Es wird keine detaillierte Strömungsmechanik modelliert.
      // Stattdessen wird angenommen:
      // höhere Motordrehzahl -> höherer Volumenstrom -> höherer Luftmassenstrom.

      parameter Real n_max = 110000
        "Maximale Motordrehzahl in rpm; Quelle: Dyson Digital Motor V9, ca. 110000 rpm";

      parameter Modelica.Units.SI.VolumeFlowRate V_dot_max = 0.013
        "Maximaler Volumenstrom in m3/s; Quelle: Dyson Supersonic Angabe ca. 13 l/s, umgerechnet in m3/s";

      parameter Modelica.Units.SI.Density rho_L = 1.2
        "Luftdichte in kg/m3; Modellannahme für Luft bei Raumtemperatur";

      Modelica.Blocks.Interfaces.RealInput n
        "Motordrehzahl in rpm"
        annotation (Placement(
          transformation(extent={{-120,-20},{-80,20}}),
          iconTransformation(extent={{-120,-20},{-80,20}})));

      Modelica.Blocks.Interfaces.RealOutput m_dot
        "Luftmassenstrom in kg/s"
        annotation (Placement(
          transformation(extent={{100,-10},{120,10}}),
          iconTransformation(extent={{100,-10},{120,10}})));

    protected
      Real speedFraction
        "Normierte Drehzahl zwischen 0 und 1";

    equation
      // Die Drehzahl wird auf den Bereich 0 bis 1 normiert.
      speedFraction = min(max(n / n_max, 0), 1);

      // Umrechnung von Volumenstrom in Massenstrom: m_dot = rho * V_dot
      m_dot = rho_L * V_dot_max * speedFraction;

    end Propeller;

    model Luftstrom
      // Dynamisches Luftstrommodell eines Haarföhns.
      // Die Luft im Heizkanal wird durch eine thermische Kapazität C_L modelliert.
      // Dadurch erwärmt sich die Ausblasluft mit einer realistischen Verzögerung,
      // anstatt sofort auf die Heizdrahttemperatur zu springen (quasistationär).
      //
      // Energiebilanz:
      // - Frischluft strömt mit T_ein ein und kühlt den Kanal.
      // - Der Heizdraht gibt Wärme über port_heiz ab.
      // - Das Haarmodell nimmt Wärme über port_aus auf.

      parameter Modelica.Units.SI.SpecificHeatCapacity cp_L = 1005
        "Spezifische Wärmekapazität von Luft in J/(kg.K); Literaturwert für Luft bei ca. 20 °C";

      parameter Modelica.Units.SI.Temperature T_ein = 293.15
        "Eintrittstemperatur der Luft in K; Modellannahme: Raumtemperatur 20 °C";

      parameter Modelica.Units.SI.MassFlowRate m_dot_min = 0.001
        "Minimaler Luftmassenstrom in kg/s; Modellannahme zur Vermeidung von Division durch 0";

      parameter Modelica.Units.SI.HeatCapacity C_L = 8
        "Thermische Kapazität der Luft im Heizkanal in J/K; Modellannahme";

      Modelica.Blocks.Interfaces.RealInput m_dot
        "Luftmassenstrom in kg/s; kommt vom Propeller"
        annotation (Placement(
          transformation(extent={{-120,40},{-80,80}}),
          iconTransformation(extent={{-120,40},{-80,80}})));

      Modelica.Blocks.Interfaces.RealOutput T_L
        "Ausblastemperatur der Luft in K"
        annotation (Placement(
          transformation(extent={{100,-40},{120,0}}),
          iconTransformation(extent={{100,-40},{120,0}})));

      Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a port_heiz
        "Thermischer Eingang: Wärmeaufnahme vom Heizdraht"
        annotation (Placement(
          transformation(extent={{-110,-70},{-90,-50}}),
          iconTransformation(extent={{-110,-70},{-90,-50}})));

      Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_b port_aus
        "Thermischer Ausgang: Wärmeabgabe an nachgeschaltete Komponenten, z. B. Haarmodell"
        annotation (Placement(
          transformation(extent={{90,40},{110,60}}),
          iconTransformation(extent={{90,40},{110,60}})));

    protected
      Modelica.Units.SI.MassFlowRate m_eff
        "Wirksamer Luftmassenstrom mit Untergrenze";

      Modelica.Units.SI.Temperature T_L_dyn(start=293.15)
        "Dynamische Lufttemperatur im Kanal in K";

    equation
      m_eff = max(m_dot, m_dot_min);

      // Dynamische Energiebilanz der Luft im Heizkanal:
      // C_L * dT/dt = Wärme vom Heizdraht + Wärme zum Haar + Konvektionskühlung durch Frischluft.
      // Der Term m_eff * cp_L * (T_ein - T_L_dyn) modelliert den kontinuierlichen
      // Zustrom kalter Frischluft, der den Kanal kühlt.
      C_L * der(T_L_dyn) = port_heiz.Q_flow + port_aus.Q_flow
                           + m_eff * cp_L * (T_ein - T_L_dyn);

      T_L       = T_L_dyn;
      port_heiz.T = T_L_dyn;
      port_aus.T  = T_L_dyn;

    end Luftstrom;

    model Gehaeuse
      // Vereinfachtes thermisches Modell des Gehäuses eines Haarföhns.
      // Das Gehäuse nimmt Wärme über einen HeatPort auf und gibt Wärme an die Umgebung ab.
      //
      // Modellvereinfachung:
      // Das Gehäuse wird als eine homogene thermische Masse betrachtet.
      // Es wird keine detaillierte Geometrie oder Materialverteilung modelliert.

      parameter Modelica.Units.SI.Mass m_Geh = 0.3
        "Masse des Gehäuses in kg; Modellannahme";

      parameter Modelica.Units.SI.SpecificHeatCapacity cp_Geh = 1300
        "Spezifische Wärmekapazität des Gehäuses in J/(kg.K); angenäherter Wert für Kunststoff/ABS, z. B. MatWeb";

      parameter Modelica.Units.SI.ThermalConductance G_amb = 2.0
        "Wärmeleitwert vom Gehäuse zur Umgebung in W/K; Modellannahme";

      parameter Modelica.Units.SI.Temperature T_amb = 293.15
        "Umgebungstemperatur in K; Modellannahme: Raumtemperatur 20 °C";

      parameter Modelica.Units.SI.Temperature T_start = 293.15
        "Starttemperatur des Gehäuses in K; Modellannahme: Raumtemperatur 20 °C";

      Modelica.Units.SI.Temperature T_Geh(start=T_start)
        "Temperatur des Gehäuses";

      Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a port
        "Thermischer Anschluss zur Wärmeaufnahme vom Heizdraht"
        annotation (Placement(
          transformation(extent={{-110,-10},{-90,10}}),
          iconTransformation(extent={{-110,-10},{-90,10}})));

    equation
      // Energiebilanz des Gehäuses:
      // port.Q_flow ist positiv, wenn Wärme in das Gehäuse hinein fließt.
      // Über G_amb wird Wärme an die Umgebung abgegeben.
      m_Geh * cp_Geh * der(T_Geh) = port.Q_flow - G_amb * (T_Geh - T_amb);
      port.T = T_Geh;

    end Gehaeuse;

    model Haarmodell
      // Thermisches Modell des Haars mit Verdunstungseffekt.
      // Das Haar wird als homogene thermische Masse mit Feuchtigkeitsgehalt modelliert.
      //
      // Solange das Haar feucht ist (feuchte > 0), verbraucht die Verdunstung einen Teil
      // der zugeführten Wärme. Das Haar erwärmt sich deshalb anfangs langsamer.
      // Sobald das Haar trocken ist (feuchte = 0), steigt die Haartemperatur schneller an.
      //
      // Dieser Zweiphaseneffekt (Trocknungsphase / Erwärmungsphase) ist das physikalisch
      // wichtigste Merkmal beim Betrieb eines Haarföhns.

      parameter Modelica.Units.SI.Mass m_H = 0.05
        "Haarmasse in kg; Modellannahme: ca. 50 g Haar";

      parameter Modelica.Units.SI.SpecificHeatCapacity cp_H = 1300
        "Spezifische Wärmekapazität des Haars in J/(kg.K); Literaturwert für Keratin";

      parameter Modelica.Units.SI.Temperature T_start = 293.15
        "Starttemperatur des Haars in K; Modellannahme: Raumtemperatur 20 °C";

      parameter Real feuchte_start = 0.3
        "Anfangsfeuchtegehalt des Haars; 0.3 entspricht 30 % Wasseranteil; Modellannahme";

      parameter Modelica.Units.SI.SpecificEnthalpy h_verd = 2.45e6
        "Verdampfungsenthalpie von Wasser in J/kg; Literaturwert bei 20 °C";

      parameter Real k_verd = 0.00002
        "Verdunstungskoeffizient in 1/(K*s); bestimmt die Trocknungsgeschwindigkeit; Modellannahme";

      Modelica.Units.SI.Temperature T_H(start=T_start)
        "Temperatur des Haarmodells";

      Real feuchte(start=feuchte_start)
        "Aktueller Feuchtegehalt des Haars; sinkt von feuchte_start auf 0";

      Modelica.Units.SI.HeatFlowRate Q_verd
        "Verdunstungswärmestrom in W; wird der Haarerwärmung entzogen";

      Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a port
        "Thermischer Anschluss zur Wärmeaufnahme aus dem Luftstrom"
        annotation (Placement(
          transformation(extent={{-110,-10},{-90,10}}),
          iconTransformation(extent={{-110,-10},{-90,10}})));

    equation
      // Verdunstungswärmestrom: proportional zu verbleibender Feuchtigkeit und
      // Temperaturdifferenz zur Umgebung.
      // max(..., 0) verhindert negative Werte und sorgt für numerische Stabilität.
      Q_verd = k_verd * max(feuchte, 0) * h_verd * max(T_H - 293.15, 0);

      // Feuchtigkeitsabnahme durch Verdunstung.
      der(feuchte) = -k_verd * max(feuchte, 0) * max(T_H - 293.15, 0);

      // Energiebilanz: Zugeführte Wärme minus Verdunstungswärme ergibt Haarerwärmung.
      m_H * cp_H * der(T_H) = port.Q_flow - Q_verd;

      port.T = T_H;

    end Haarmodell;

  end Components;

  package System

    model Dyson_Ungeregelt
      // Ungeregeltes System: Heizdraht läuft mit konstantem Signal u_regler = 1.
      // Die Heizleistung ist immer maximal, bis die Sicherheitsabschaltung greift.

      parameter Integer fanLevel(min=1, max=3) = 3
        "Luftstromstufe: 1=niedrig, 2=mittel, 3=hoch; wird an Motor weitergegeben";

      Components.Motor motor(fanLevel=fanLevel)
        annotation (Placement(transformation(extent={{-88,48},{-68,68}})));
      Components.Propeller propeller
        annotation (Placement(transformation(extent={{-40,48},{-20,68}})));
      Components.Heizdraht heizdraht
        annotation (Placement(transformation(extent={{-54,-8},{-30,16}})));
      Components.Luftstrom luftstrom
        annotation (Placement(transformation(extent={{0,48},{20,68}})));
      Components.Gehaeuse gehaeuse
        annotation (Placement(transformation(extent={{8,-52},{28,-32}})));
      Components.Haarmodell haarmodell
        annotation (Placement(transformation(extent={{76,14},{96,34}})));
      Modelica.Blocks.Sources.Constant const(k=1)
        annotation (Placement(transformation(extent={{-90,-6},{-70,14}})));
      Modelica.Thermal.HeatTransfer.Components.ThermalConductor G_Heiz_Geh(G=1)
        annotation (Placement(transformation(extent={{-34,-64},{-4,-34}})));
      Modelica.Thermal.HeatTransfer.Components.ThermalConductor G_Luft_Haar(G=5)
        annotation (Placement(transformation(extent={{38,42},{66,70}})));
      Modelica.Thermal.HeatTransfer.Components.ThermalConductor G_Heiz_Luft(G=20)
        annotation (Placement(transformation(extent={{2,-10},{34,22}})));

    equation
      connect(const.y, heizdraht.u_regler)
        annotation (Line(points={{-69,4},{-54,4}}, color={0,0,127}));
      connect(motor.n, propeller.n)
        annotation (Line(points={{-67,58},{-40,58}}, color={0,0,127}));
      connect(propeller.m_dot, luftstrom.m_dot)
        annotation (Line(points={{-19,58},{-8,58},{-8,64},{0,64}}, color={0,0,127}));
      connect(heizdraht.port, G_Heiz_Luft.port_a)
        annotation (Line(points={{-30,4},{-4,4},{-4,6},{2,6}}, color={191,0,0}));
      connect(G_Heiz_Luft.port_b, luftstrom.port_heiz)
        annotation (Line(points={{34,6},{38,6},{38,38},{-6,38},{-6,52},{0,52}}, color={191,0,0}));
      connect(heizdraht.port, G_Heiz_Geh.port_a)
        annotation (Line(points={{-30,4},{-18,4},{-18,-30},{-38,-30},{-38,-49},{-34,-49}}, color={191,0,0}));
      connect(G_Heiz_Geh.port_b, gehaeuse.port)
        annotation (Line(points={{-4,-49},{2,-49},{2,-42},{8,-42}}, color={191,0,0}));
      connect(luftstrom.port_aus, G_Luft_Haar.port_a)
        annotation (Line(points={{20,63},{32,63},{32,56},{38,56}}, color={191,0,0}));
      connect(G_Luft_Haar.port_b, haarmodell.port)
        annotation (Line(points={{66,56},{70,56},{70,24},{76,24}}, color={191,0,0}));

    end Dyson_Ungeregelt;

    model Dyson_Geregelt
      // Geregeltes System: Ein PI-Regler hält die Lufttemperatur auf T_soll = 100 °C.
      // Der Regler passt das Heizdrahtsignal u_regler kontinuierlich an.

      parameter Integer fanLevel(min=1, max=3) = 3
        "Luftstromstufe: 1=niedrig, 2=mittel, 3=hoch; wird an Motor weitergegeben";

      Components.Motor motor(fanLevel=fanLevel)
        annotation (Placement(transformation(extent={{-88,48},{-68,68}})));
      Components.Propeller propeller
        annotation (Placement(transformation(extent={{-40,48},{-20,68}})));
      Components.Heizdraht heizdraht
        annotation (Placement(transformation(extent={{-20,-18},{4,6}})));
      Components.Luftstrom luftstrom
        annotation (Placement(transformation(extent={{0,48},{20,68}})));
      Components.Gehaeuse gehaeuse
        annotation (Placement(transformation(extent={{64,-48},{84,-28}})));
      Components.Haarmodell haarmodell
        annotation (Placement(transformation(extent={{76,14},{96,34}})));
      Modelica.Blocks.Sources.Constant T_soll(k=373.15)
        annotation (Placement(transformation(extent={{-90,-6},{-70,14}})));
      Modelica.Thermal.HeatTransfer.Components.ThermalConductor G_Heiz_Geh(G=1)
        annotation (Placement(transformation(extent={{-16,-80},{14,-50}})));
      Modelica.Thermal.HeatTransfer.Components.ThermalConductor G_Luft_Haar(G=5)
        annotation (Placement(transformation(extent={{38,42},{66,70}})));
      Modelica.Thermal.HeatTransfer.Components.ThermalConductor G_Heiz_Luft(G=20)
        annotation (Placement(transformation(extent={{26,-12},{58,20}})));
      Modelica.Blocks.Continuous.LimPID PID(
        controllerType=Modelica.Blocks.Types.SimpleController.PI,
        k=0.03,
        Ti=5,
        yMax=1,
        yMin=0,
        initType=Modelica.Blocks.Types.Init.InitialOutput,
        y_start=1)
        annotation (Placement(transformation(extent={{-58,26},{-38,46}})));

    equation
      connect(motor.n, propeller.n)
        annotation (Line(points={{-67,58},{-40,58}}, color={0,0,127}));
      connect(propeller.m_dot, luftstrom.m_dot)
        annotation (Line(points={{-19,58},{-8,58},{-8,64},{0,64}}, color={0,0,127}));
      connect(heizdraht.port, G_Heiz_Luft.port_a)
        annotation (Line(points={{4,-6},{20,-6},{20,4},{26,4}}, color={191,0,0}));
      connect(G_Heiz_Luft.port_b, luftstrom.port_heiz)
        annotation (Line(points={{58,4},{62,4},{62,30},{-6,30},{-6,52},{0,52}}, color={191,0,0}));
      connect(heizdraht.port, G_Heiz_Geh.port_a)
        annotation (Line(points={{4,-6},{8,-6},{8,-46},{-20,-46},{-20,-65},{-16,-65}}, color={191,0,0}));
      connect(G_Heiz_Geh.port_b, gehaeuse.port)
        annotation (Line(points={{14,-65},{58,-65},{58,-38},{64,-38}}, color={191,0,0}));
      connect(luftstrom.port_aus, G_Luft_Haar.port_a)
        annotation (Line(points={{20,63},{32,63},{32,56},{38,56}}, color={191,0,0}));
      connect(G_Luft_Haar.port_b, haarmodell.port)
        annotation (Line(points={{66,56},{70,56},{70,24},{76,24}}, color={191,0,0}));
      connect(PID.u_s, T_soll.y)
        annotation (Line(points={{-60,36},{-68,36},{-68,18},{-66,18},{-66,4},{-69,4}}, color={0,0,127}));
      connect(luftstrom.T_L, PID.u_m)
        annotation (Line(points={{21,56},{26,56},{26,26},{-34,26},{-34,14},{-48,14},{-48,24}}, color={0,0,127}));
      connect(PID.y, heizdraht.u_regler)
        annotation (Line(points={{-37,36},{-26,36},{-26,2},{-28,2},{-28,-6},{-20,-6}}, color={0,0,127}));

    end Dyson_Geregelt;

  end System;

  package Tests

    model Test_01_Geregelt_vs_Ungeregelt
      // Vergleich: Geregeltes vs. ungeregeltes System bei Luftstufe 3 (hoch).
      //
      // Erwartetes Ergebnis:
      // - Dyson_Ungeregelt: Lufttemperatur steigt schnell, überschreitet Sollwert,
      //   Sicherheitsabschaltung kann eingreifen.
      // - Dyson_Geregelt: Lufttemperatur nähert sich T_soll = 100 °C und bleibt stabil.
      //
      // Simulationszeit: 300 s, um thermisches Einschwingens sichtbar zu machen.

      DysonModel.System.Dyson_Ungeregelt dyson_Ungeregelt
        annotation (Placement(transformation(extent={{-78,0},{-58,20}})));
      DysonModel.System.Dyson_Geregelt dyson_Geregelt
        annotation (Placement(transformation(extent={{26,0},{46,20}})));

      annotation (experiment(StopTime=300, __Dymola_Algorithm="Dassl"));
    end Test_01_Geregelt_vs_Ungeregelt;

    model Test_02_Luftstromstufen
      // Vergleich der drei Luftstromstufen im ungeregelten Betrieb.
      //
      // Erwartetes Ergebnis:
      // - Stufe 1 (niedrig): wenig Luftmassenstrom, Luft wird heißer, Haar trocknet langsamer.
      // - Stufe 3 (hoch): viel Luftmassenstrom, Luft bleibt kühler, Haar trocknet schneller.
      //
      // Simulationszeit: 300 s.

      DysonModel.System.Dyson_Ungeregelt dyson_Stufe1(fanLevel=1)
        annotation (Placement(transformation(extent={{-78,0},{-58,20}})));
      DysonModel.System.Dyson_Ungeregelt dyson_Stufe2(fanLevel=2)
        annotation (Placement(transformation(extent={{-18,0},{2,20}})));
      DysonModel.System.Dyson_Ungeregelt dyson_Stufe3(fanLevel=3)
        annotation (Placement(transformation(extent={{40,0},{60,20}})));

      annotation (experiment(StopTime=300, __Dymola_Algorithm="Dassl"));
    end Test_02_Luftstromstufen;

    model Test_03_Haartrocknung
      // Trocknungsverhalten des Haars im geregelten Betrieb.
      //
      // Zu beobachtende Größen:
      // - feuchte: sinkt von 0.3 auf 0 (Haar trocknet vollständig).
      // - T_H (Haartemperatur): steigt anfangs langsam (Verdunstung kühlt),
      //   dann schneller nach dem Abtrocknen.
      // - Q_verd: Verdunstungswärmestrom, wird 0 wenn Haar trocken ist.
      //
      // Simulationszeit: 300 s.

      DysonModel.System.Dyson_Geregelt dyson_Geregelt
        annotation (Placement(transformation(extent={{-20,0},{0,20}})));

      annotation (experiment(StopTime=300, __Dymola_Algorithm="Dassl"));
    end Test_03_Haartrocknung;

  end Tests;

  annotation (uses(Modelica(version="4.1.0")));
end DysonModel;
